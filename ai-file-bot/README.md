# AI 文件分析 Bot

这个服务用于给 Mattermost 增加附件内容分析能力。

它会作为一个独立的 Mattermost 机器人账号运行，并监听机器人已加入的频道。当用户在频道里提到这个机器人时，它会优先查找当前话题线程里的附件；如果当前线程没有附件，则会继续查找该频道里最近的附件消息。找到文件后，服务会提取文件文本内容，并把内容发送给兼容 OpenAI API 的大模型进行分析。

## 支持的文件类型

- 可复制文本的 PDF
- DOCX
- XLSX
- PPTX
- TXT、Markdown、CSV、日志文件

注意：扫描版 PDF 和纯图片文件目前不会做 OCR 识别。

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

- 当前不会读取图片里的文字。
- 扫描版 PDF 通常提取不到正文内容。
- 文件过大时会截断部分文本后再发送给大模型。
- 机器人只能分析它已经加入的频道里的附件。
