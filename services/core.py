"""
核心基础设施模块
提供HTTP客户端池管理
"""

import httpx
import os
from typing import Dict, Optional, Any
import re

# 导入代理配置支持
try:
    from httpx_socks import AsyncProxyTransport
    _SOCKS_AVAILABLE = True
except ImportError:
    _SOCKS_AVAILABLE = False

# 导入环境变量代理配置
try:
    from ..utils.proxy_config import get_socks5_proxy_url
    _PROXY_CONFIG_AVAILABLE = True
except ImportError:
    _PROXY_CONFIG_AVAILABLE = False

class HTTPClientPool:
    """
    HTTP客户端池
    管理持久化的 httpx.AsyncClient，支持连接复用
    """
    _clients: Dict[str, httpx.AsyncClient] = {}
    _loop_id: Optional[int] = None  # 记录创建客户端时的事件循环ID
    
    @classmethod
    def _check_loop_change(cls) -> bool:
        """
        检测事件循环是否发生变化
        返回: True = 循环已变化，需要清理旧客户端
        """
        try:
            import asyncio
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
            
            if cls._loop_id is None:
                cls._loop_id = current_loop_id
                return False
            
            if cls._loop_id != current_loop_id:
                # 事件循环已变化，清理所有旧客户端
                cls._loop_id = current_loop_id
                # 不能 await close，直接丢弃引用（让 GC 处理）
                cls._clients.clear()
                return True
            
            return False
        except RuntimeError:
            # 没有运行中的事件循环，保守处理
            return False
    
    @classmethod
    def get_client(
        cls,
        provider: str,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        proxy: Optional[str] = None,
        verify_ssl: bool = True,
        **kwargs
    ) -> httpx.AsyncClient:
        """
        获取或创建HTTP客户端（支持连接复用和 SOCKS5 代理）
        
        参数:
            provider: 服务商标识（用于日志）
            base_url: API基础URL，作为缓存的Key
            timeout: 超时时间（秒）
            proxy: 代理设置（可选，默认从环境变量读取）
            verify_ssl: 是否验证SSL证书
        """
        # 检测事件循环变化，必要时清理旧客户端
        cls._check_loop_change()
        
        # 使用 base_url 作为唯一标识进行缓存
        cache_key = base_url or provider
        
        if cache_key in cls._clients:
            client = cls._clients[cache_key]
            if not client.is_closed:
                return client

        # 创建新客户端
        client_kwargs = {
            'timeout': httpx.Timeout(timeout, connect=10.0, read=timeout, write=60.0),
            'verify': verify_ssl,
            'follow_redirects': True,
            'http2': False,
            # 关键修复：禁用系统环境变量代理配置
            # 避免 HTTP_PROXY/HTTPS_PROXY 导致 localhost 请求被代理拦截返回 502
            'trust_env': False,
            # 设置连接池保持连接
            'limits': httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0)
        }
        
        # 优先使用传入的 proxy 参数，否则从环境变量读取 SOCKS5 代理
        proxy_url = proxy
        if not proxy_url and _PROXY_CONFIG_AVAILABLE:
            proxy_url = get_socks5_proxy_url()
        
        # 配置 SOCKS5 代理
        if proxy_url and _SOCKS_AVAILABLE:
            # 检查是否为 SOCKS5 代理
            if proxy_url.startswith(('socks5://', 'socks5h://', 'socks4://', 'socks4h://')):
                try:
                    # 使用 httpx-socks 的 AsyncProxyTransport
                    transport = AsyncProxyTransport.from_url(proxy_url)
                    client_kwargs['transport'] = transport
                except Exception as e:
                    import logging
                    logging.warning(f"[HTTPClientPool] SOCKS5 代理配置失败: {e}, 将不使用代理")
            else:
                # 非 SOCKS5 代理，使用 httpx 原生代理支持
                client_kwargs['proxies'] = proxy_url
        elif proxy_url and not _SOCKS_AVAILABLE:
            # 配置了代理但 httpx-socks 不可用
            import logging
            logging.warning(f"[HTTPClientPool] SOCKS5 代理已配置但 httpx-socks 未安装: {proxy_url}")
            logging.warning("[HTTPClientPool] 请运行: pip install 'httpx-socks[asyncio]'")
        
        if proxy and proxy_url and proxy_url.startswith(('http://', 'https://')):
            # 如果同时传入了 http 代理参数和配置了 SOCKS5，使用传入的 http proxy
            import logging
            logging.warning(f"[HTTPClientPool] 同时传入了 http proxy 参数 ({proxy}) 和配置了 SOCKS5 代理 ({proxy_url})，使用传入的 http proxy")
            client_kwargs['proxies'] = proxy
        
        client_kwargs.update(kwargs)
        
        client = httpx.AsyncClient(**client_kwargs)
        cls._clients[cache_key] = client
        
        return client

    
    @classmethod
    async def close_all(cls):
        """关闭所有已创建的客户端，彻底释放资源"""
        for key in list(cls._clients.keys()):
            client = cls._clients.pop(key)
            try:
                await client.aclose()
            except:
                pass


# Logger 类已移除，请直接从 ..utils.common 导入 log_prepare, log_complete, log_error 等函数使用。



class BaseAPIService:
    """
    API服务抽象基类
    所有服务（LLM, VLM, Baidu）的基础
    """
    
    def __init__(self, http_client_pool: HTTPClientPool = None):
        """
        初始化基类
        
        参数:
            http_client_pool: HTTP客户端池（可选，默认使用全局池）
        """
        self.http_client_pool = http_client_pool or HTTPClientPool
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取服务配置（子类必须实现）
        
        返回:
            Dict: 配置字典
        """
        raise NotImplementedError("子类必须实现 get_config 方法")
    
    async def handle_error(self, error: Exception, provider: str) -> Dict[str, Any]:
        """
        统一错误处理
        
        参数:
            error: 异常对象
            provider: 服务商标识
        
        返回:
            Dict: 错误响应
        """
        from ..utils.common import format_api_error
        error_message = format_api_error(error, provider)
        return {
            "success": False,
            "error": error_message
        }
