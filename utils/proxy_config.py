"""
代理配置管理模块
通过 .env 文件管理 SOCKS5 代理配置
"""

import os
from typing import Optional

# 尝试导入 python-dotenv，如果不存在则使用基本的环境变量读取
try:
    from dotenv import load_dotenv

    def _load_env_file():
        """加载 .env 文件"""
        # 尝试加载项目根目录的 .env
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(env_path, override=True)
        load_dotenv(override=True)  # 也尝试从当前目录加载

except ImportError:
    def _load_env_file():
        """python-dotenv 未安装时的降级处理"""
        # 不做任何处理，直接使用系统环境变量
        pass


def get_socks5_proxy_url() -> Optional[str]:
    """
    获取 SOCKS5 代理 URL

    返回:
        Optional[str]: 代理 URL，如果未配置则返回 None
    """
    # 确保 .env 文件已加载
    _load_env_file()

    # 检查是否启用代理
    proxy_enabled = os.getenv('PROXY_ENABLED', '').lower()
    proxy_url = os.getenv('SOCKS5_PROXY_URL', '').strip()

    # 如果明确设置为 false，则禁用
    if proxy_enabled == 'false':
        return None

    # 如果明确设置为 true 且 URL 为空，视为未配置
    if proxy_enabled == 'true' and not proxy_url:
        return None

    # 如果 proxy_enabled 未设置，则根据 URL 是否存在判断
    if not proxy_enabled and not proxy_url:
        return None

    return proxy_url if proxy_url else None


def get_proxy_timeout() -> float:
    """
    获取代理超时时间

    返回:
        float: 超时时间（秒），默认 30
    """
    _load_env_file()
    timeout = os.getenv('PROXY_TIMEOUT', '30')
    try:
        return float(timeout)
    except ValueError:
        return 30.0


def get_proxy_enabled() -> bool:
    """
    检查代理是否启用

    返回:
        bool: 是否启用代理
    """
    _load_env_file()
    proxy_enabled = os.getenv('PROXY_ENABLED', '').lower()
    proxy_url = os.getenv('SOCKS5_PROXY_URL', '').strip()

    # 明确设置为 false
    if proxy_enabled == 'false':
        return False

    # 明确设置为 true
    if proxy_enabled == 'true':
        return bool(proxy_url)

    # 未设置，根据 URL 是否存在判断
    return bool(proxy_url)


def get_http_proxy_for_trust_env() -> Optional[dict]:
    """
    获取用于 trust_env=True 的 HTTP 代理配置字典

    注意：httpx 的 trust_env 读取 HTTP_PROXY/HTTPS_PROXY 等环境变量
    但对于 SOCKS5 代理，需要使用 httpx-socks 库提供的 transport

    返回:
        Optional[dict]: 包含 http 和 https 代理的字典，如果未配置则返回 None
    """
    proxy_url = get_socks5_proxy_url()
    if not proxy_url:
        return None

    # httpx 的 trust_env 不直接支持 SOCKS5
    # 这里返回 None，实际 SOCKS5 支持通过 httpx-socks 的 transport 实现
    return None
