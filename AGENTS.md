# ComfyUI Prompt Assistant - Agent 指南

本文档提供代理（Agent）开发者在 ComfyUI Prompt Assistant 项目中工作时所需的上下文信息。

## 项目概述

**项目名称**: ComfyUI Prompt Assistant (提示词小助手)
**版本**: 2.0.4
**类型**: ComfyUI 插件
**功能**: 提示词优化、翻译、图像/视频反推、标签管理

## 项目结构

```
ComfyUI-Prompt-Assistant-z/
├── __init__.py           # 插件入口，节点注册
├── server.py             # API 路由和异步任务处理
├── config_manager.py     # 配置管理（JSON/CSV）
├── pyproject.toml        # 项目元数据
├── requirements.txt      # Python 依赖
├── node/                 # ComfyUI 节点
│   ├── base/            # 节点基类
│   ├── translate_node.py, expand_node.py
│   ├── image_caption_node.py, video_caption_node.py
│   └── kontext_preset_node.py
├── services/             # 服务层（llm, vlm, baidu, openai_base）
├── utils/                # 工具函数（common, image, video）
└── js/                   # 前端代码（modules, services, utils）
```

## 构建和测试命令

**注意**: 此项目没有配置测试框架或构建脚本。ComfyUI 会自动加载插件。

### 安装依赖
```bash
pip install -r requirements.txt
```

### 开发调试
- 重启 ComfyUI 以加载插件更改
- 控制台日志显示插件初始化信息：`✨提示词小助手 V{VERSION} 已启动`

### 配置文件位置
- 用户配置：`ComfyUI/user/default/prompt-assistant/`
- 插件配置：`插件目录/config/`

## 代码风格指南

### Python 代码风格

#### 导入顺序
1. 标准库导入 2. 第三方库导入 3. 本项目导入（相对导入）

```python
import os
from typing import Optional, Dict, Any
import httpx
from aiohttp import web
from .config_manager import config_manager
```

#### 命名约定
- **类名**: PascalCase (例: `ConfigManager`)
- **函数/变量**: snake_case (例: `get_config`)
- **常量**: UPPER_SNAKE_CASE (例: `PREFIX`, `ERROR_PREFIX`)
- **私有方法**: `_prefix` (例: `_load_template`)

#### 缩进和格式
- 使用 **2 空格缩进**
- 函数间用空行分隔
- 使用中文注释和 docstring

#### 类型提示
使用 `typing` 模块（可选但推荐）

```python
from typing import Optional, Dict, Any
async def translate(text: str, from_lang: str = 'auto') -> Dict[str, Any]: ...
```

#### 错误处理
- 使用 try-except 块
- 返回统一格式：`{"success": bool, "data": Any, "error": str}`
- 使用 `format_api_error()` 格式化 API 错误

#### 日志
使用统一的日志前缀常量（从 `utils/common.py` 导入）：

```python
from utils.common import PREFIX, ERROR_PREFIX, PROCESS_PREFIX, REQUEST_PREFIX, WARN_PREFIX
```

使用进度条（`ProgressBar` 类）：

```python
from utils.common import ProgressBar
pbar = ProgressBar(request_id=req_id, service_name="Ollama", streaming=True)
```

#### 异步编程
- 使用 `asyncio` 进行异步操作
- 使用 `async with` 进行上下文管理
- API 端点必须是 async 函数

#### 配置管理
- JSON 配置使用原子性写入（`_atomic_write_json`）
- CSV 标签文件支持多种编码（utf-8-sig, gbk, utf-8）

```python
from config_manager import config_manager
config = config_manager.get_llm_config()
config_manager.save_config(config)
```

### JavaScript 前端风格

#### 模块导入
使用 ES6 模块导入：

```javascript
import { app } from "../../../scripts/app.js";
import { promptAssistant } from './modules/PromptAssistant.js';
```

#### 注释
使用 JSDoc 风格注释

#### 全局状态
使用 `window` 对象共享状态：

```javascript
window.FEATURES = ASSISTANT_FEATURES;
window.promptAssistant = promptAssistant;
app.promptAssistant = promptAssistant;
```

## 关键模式

### 节点开发
所有节点继承自 `BaseNode`，使用 `_execute_with_interrupt()` 支持中断

### API 开发
所有 API 路由使用 aiohttp，通过 `PromptServer.instance.routes` 注册，使用 async 函数

### 服务开发
服务类继承自 `OpenAICompatibleService`，返回统一格式的字典

## 版本管理

版本号定义在 `pyproject.toml` 中，启动时自动注入到前端：`window.PromptAssistant_Version`

## 注意事项

1. **编码**: 始终使用 UTF-8 编码
2. **日志**: 使用统一的日志前缀，避免直接 print
3. **错误**: 使用 `format_api_error()` 格式化错误信息
4. **异步**: API 端点必须是 async 函数
5. **安全**: API Key 通过 `mask_api_key()` 掩码后再返回给前端
6. **配置**: 使用 `config_manager` 统一管理配置，不要直接读写文件
7. **线程**: 节点执行使用 `_execute_with_interrupt()` 支持中断
8. **兼容性**: 保持向后兼容，检查配置版本号
