# Swagger UI 加载问题修复方案

## 问题描述
访问 `http://localhost:8000/docs` 时出现以下错误：
- `swagger-ui-bundle.js` 加载超时 (ERR_CONNECTION_TIMED_OUT)
- `SwaggerUIBundle is not defined` 引用错误

## 解决方案

### 方案1：使用 jsdelivr CDN（已实施）✅

已将 Swagger UI 的 CDN 从 `unpkg.com` 更改为 `cdn.jsdelivr.net`，后者在国内访问更稳定。

**修改位置**：`backend/main.py` 第 77-79 行

```python
swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
swagger_favicon_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/favicon-32x32.png",
```

### 方案2：使用本地 Swagger UI 文件（备用方案）

如果 CDN 仍然无法访问，可以使用本地静态文件：

#### 步骤1：安装 swagger-ui-dist

```bash
cd backend
pip install swagger-ui-dist
```

#### 步骤2：修改 main.py

将 Swagger UI 配置改为 `None`，让 FastAPI 使用默认的本地文件：

```python
# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于FastAPI + AI大模型的智能台风分析系统",
    lifespan=lifespan,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "tryItOutEnabled": True,
    },
    # 不指定 CDN，使用本地文件
    # swagger_js_url=None,
    # swagger_css_url=None,
)
```

### 方案3：使用国内镜像 CDN

如果方案1和方案2都不行，可以尝试其他国内 CDN：

#### 选项A：BootCDN
```python
swagger_js_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.9.0/swagger-ui-bundle.js",
swagger_css_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.9.0/swagger-ui.css",
```

#### 选项B：字节跳动 CDN
```python
swagger_js_url="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/swagger-ui/4.10.3/swagger-ui-bundle.js",
swagger_css_url="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/swagger-ui/4.10.3/swagger-ui.css",
```

## 测试步骤

1. 重启后端服务：
   ```bash
   cd backend
   python main.py
   ```

2. 访问 Swagger UI：
   ```
   http://localhost:8000/docs
   ```

3. 检查浏览器控制台是否还有错误

## 验证成功标志

- ✅ Swagger UI 页面正常显示
- ✅ 可以看到所有 API 端点列表
- ✅ 可以展开和测试 API
- ✅ 浏览器控制台无 JavaScript 错误

## 其他说明

- 如果使用代理或 VPN，可能会影响 CDN 访问
- 建议在生产环境使用本地静态文件（方案2）以提高稳定性
- FastAPI 默认会尝试从 `https://cdn.jsdelivr.net` 加载资源

