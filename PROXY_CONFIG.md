# SOCKS5 代理配置文档

本项目支持通过 `.env` 文件配置 SOCKS5 代理来访问所有 API（翻译、图片反推、提示词扩写等）。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

这将自动安装以下依赖：
- `httpx` - HTTP 客户端库（已有）
- `python-dotenv` - 环境变量管理（新增）
- `httpx-socks[asyncio]` - SOCKS5 代理支持（新增）

### 2. 创建配置文件

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

### 3. 编辑配置

编辑 `.env` 文件，设置代理 URL：

```env
# SOCKS5 代理配置
SOCKS5_PROXY_URL=socks5://host:port

# 是否启用代理（可选）
PROXY_ENABLED=true

# 代理超时设置（可选，默认 30 秒）
PROXY_TIMEOUT=30
```

### 4. 重启 ComfyUI

重启 ComfyUI 以加载新的配置。

---

## 📝 配置说明

| 配置项 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `SOCKS5_PROXY_URL` | 代理 URL | 空 | 否 |
| `PROXY_ENABLED` | 是否启用代理 | 根据代理 URL 判断 | 否 |
| `PROXY_TIMEOUT` | 代理超时时间（秒） | 30 | 否 |

---

## 📚 使用方式

### 方式 1：使用 .env 文件（推荐）

编辑 `.env` 文件，设置代理 URL：

```env
host:port//host:port
```

### 方式 2：使用环境变量

在运行 ComfyUI 前设置环境变量：

```bash
# Windows (CMD)
set SOCKS5_PROXY_URL=socks5://host:port

# Windows (PowerShell)
$env:SOCKS5_PROXY_URL="socks5://host:port"

# Linux/Mac
export SOCKS5_PROXY_URL="socks5://host:port"
```

---

## 🔧 技术实现

### 工作原理

1. **自动读取配置**：启动时自动读取 `.env` 文件中的代理配置
2. **智能检测**：
   - 如果配置了 SOCKS5 代理且安装了 `httpx-socks`，使用 `AsyncProxyTransport`
   - 如果配置了 HTTP 代理，使用 httpx 原生代理支持
   - 如果没有配置代理，使用直连方式
3. **全局生效**：所有 API 调用（翻译、图片反推、提示词扩写等）都会使用代理

### 架构设计

```
.env (环境变量配置)
    ↓
utils/proxy_config.py (配置读取)
    ↓
services/core.py (HTTPClientPool)
    ↓
所有 HTTP 请求 (LLM, VLM, Baidu, etc.)
```

### 关键代码

**services/core.py 修改**：

```python
# 导入代理配置
try:
    from httpx_socks import AsyncProxyTransport
    _SOCKS_AVAILABLE = True
except ImportError:
    _SOCKS_AVAILABLE = False

try:
    from ..utils.proxy_config import get_socks5_proxy_url
    _PROXY_CONFIG_AVAILABLE = True
except ImportError:
    _PROXY_CONFIG_AVAILABLE = False

# 在 get_client() 中使用
proxy_url = proxy or get_socks5_proxy_url()
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
```

---

## 🧩 代理格式支持

### SOCKS5 代理（推荐）

```
socks5://host:port
socks5://username:password@host:port
socks5h://host:port  # DNS 在代理端解析
```

### HTTP 代理（原生支持）

```
http://host:port
https://host:port
http://username:password@host:port
```

---

## 🚨 故障排查

### 问题：代理不生效

**解决方法**：
1. 检查 `.env` 文件是否在项目根目录
2. 确认依赖已安装：`pip install -r requirements.txt`
3. 重启 ComfyUI

### 问题：连接超时

增加超时时间：
```env
PROXY_TIMEOUT=60
```

### 问题：httpx-socks 导入失败

```bash
pip install 'httpx-socks[asyncio]'
```

---

## 🔐 安全说明

1. **敏感信息保护**：
   - `.env` 文件已添加到 `.gitignore`
   - 不要将 `.env` 文件提交到 Git 仓库
   - 仅在本地或私有仓库中使用真实的代理配置

2. **依赖安全**：
   - `httpx-socks` 为可选依赖，未安装时会优雅降级
   - 不配置代理时，使用原有直连方式

---

## 🔄 与上游合并

### 合并策略

1. **独立模块**：`utils/proxy_config.py` 是新增文件，无冲突
2. **最小修改**：`services/core.py` 仅修改 `get_client()` 方法
3. **可选依赖**：所有新增依赖都是可选的

### 合并步骤

如果上游项目更新：

1. **拉取上游更新**：
   ```bash
   git fetch upstream
   git merge upstream/main
   ```

2. **处理冲突**（如果有）：
   - `services/core.py`：手动合并代理配置逻辑
   - 其他文件：通常无冲突

3. **测试**：
   ```bash
   pip install -r requirements.txt
   ```

---

## 📦 生效范围

代理配置后，以下所有功能都会自动使用代理：

- ✅ 提示词扩写（LLM 服务）
- ✅ 文本翻译（LLM / 百度翻译服务）
- ✅ 图像反推（VLM 服务）
- ✅ 视频反推（VLM 服务）
- ✅ 所有通过 HTTPClientPool 的 API 调用

---

## 📋 文件列表

### 新建文件

| 文件 | 说明 |
|------|------|
| `.env.example` | 环境变量配置模板 |
| `utils/proxy_config.py` | 代理配置管理模块 |
| `.gitignore` | Git 忽略配置（保护敏感信息） |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `requirements.txt` | 添加 `python-dotenv` 和 `httpx-socks[asyncio]` |
| `services/core.py` | 集成 SOCKS5 代理支持到 `HTTPClientPool.get_client()` |

---

## ⚙️ 注意事项

1. **编码**：始终使用 UTF-8 编码
2. **日志**：配置错误时会在日志中显示警告信息
3. **性能**：使用持久化客户端，连接复用
4. **兼容性**：未安装 httpx-socks 时仍可使用原有功能

---

## 🌟 功能特性

- ✅ 支持 SOCKS5 代理（带认证）
- ✅ 支持 HTTP/HTTPS 代理
- ✅ 自动从环境变量读取配置
- ✅ 优雅降级（未安装依赖时仍可使用）
- ✅ 全局生效（所有 API 调用）
- ✅ 最小侵入（易于与上游合并）
- ✅ 安全性保障（敏感信息不提交）
