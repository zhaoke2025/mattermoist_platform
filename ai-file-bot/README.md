# AI 文件分析 Bot

这个服务用于给 Mattermost 增加附件内容分析能力。

它会作为一个独立的 Mattermost 机器人账号运行，并监听机器人已加入的频道。当用户在频道里提到这个机器人时，它会优先查找当前话题线程里的附件；如果当前线程没有附件，则会继续查找该频道里最近的附件消息。找到文件后，服务会提取文件文本内容，并把内容发送给兼容 OpenAI API 的大模型进行分析。

## 支持的文件类型

- 可复制文本的 PDF
- 扫描版 PDF（支持多页）
- JPG、JPEG、PNG 图片
- DOCX
- XLSX
- PPTX
- TXT、Markdown、CSV、日志文件

OCR 默认调用云端 Qwen3.5-OCR；单页请求失败或未返回有效文字时，会自动使用本地 PaddleOCR 重新识别。

## Mattermost 配置要求

1. 开启机器人账号功能。
2. 开启用户访问令牌功能。
3. 创建一个 Mattermost 机器人账号，例如 `filebot`。
4. 为机器人创建访问令牌。
5. 把机器人加入需要分析文件的团队和频道。
6. 在 `.env` 中配置机器人令牌：

```env
AI_FILE_BOT_MATTERMOST_TOKEN=你的_mattermost_bot_token
```

## 大模型配置要求

在 `.env` 中配置以下变量：

```env
AI_FILE_BOT_OPENAI_BASE_URL=https://api.deepseek.com/v1
AI_FILE_BOT_OPENAI_API_KEY=你的_api_key
AI_FILE_BOT_OPENAI_MODEL=deepseek-chat
```

这里不限定必须使用 DeepSeek，只要是兼容 OpenAI API 格式的模型服务都可以接入。

## OCR 配置要求

云端 OCR 与附件分析模型分别配置，避免把仅支持文本的模型误用于图片识别：

```env
AI_FILE_BOT_OCR_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_FILE_BOT_OCR_API_KEY=你的_DashScope_api_key
AI_FILE_BOT_OCR_MODEL=qwen3.5-ocr
AI_FILE_BOT_OCR_MAX_WORKERS=5
AI_FILE_BOT_OCR_MAX_PDF_PAGES=20
```

未配置云端 OCR 密钥时会直接使用 PaddleOCR。PaddleOCR 首次运行需要下载中文模型，模型缓存在 Docker 数据卷 `ai_file_bot_paddle_models` 中，后续重建容器不会重复下载。

## 启动方式

```powershell
docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml -f docker-compose.onlyoffice.yml -f docker-compose.postgres-local.yml -f docker-compose.ai-file-bot.yml up -d --build ai-file-bot
```

## 使用方式

推荐在文件消息下面直接回复：

```text
@filebot 分析这个文件，并总结重点
```

也可以在同一个频道里，上传附件后紧接着提到机器人：

```text
@filebot 分析最近上传的附件
```

更推荐第一种“在线程里回复”的方式，因为机器人可以更准确地定位到对应附件。

## 常见限制

- 默认最多识别 20 页 PDF，可通过 `AI_FILE_BOT_OCR_MAX_PDF_PAGES` 调整。
- PaddleOCR 兜底在 CPU 上运行，首次下载模型及首次识别耗时较长。
- 文件过大时会截断部分文本后再发送给大模型。
- 机器人只能分析它已经加入的频道里的附件。
