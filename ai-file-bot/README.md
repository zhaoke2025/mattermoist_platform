# AI File Bot

This service adds attachment analysis for Mattermost.

It runs as a separate bot account and watches channels where the bot is a member. When a user mentions the bot, it finds files in the current thread first, then nearby previous channel messages, extracts text, and sends the extracted content to an OpenAI-compatible model.

## Supported files

- PDF with selectable text
- DOCX
- XLSX
- PPTX
- TXT, Markdown, CSV, log files

Scanned PDFs and image-only files are not OCR processed.

## Required Mattermost setup

1. Enable bot accounts and user access tokens.
2. Create a Mattermost bot account, for example `filebot`.
3. Create a bot access token.
4. Add the bot to every team/channel where it should analyze files.
5. Set the token in `.env` as `AI_FILE_BOT_MATTERMOST_TOKEN`.

## Required LLM setup

Set these values in `.env`:

```env
AI_FILE_BOT_OPENAI_BASE_URL=https://api.deepseek.com/v1
AI_FILE_BOT_OPENAI_API_KEY=your_api_key
AI_FILE_BOT_OPENAI_MODEL=deepseek-chat
```

Any OpenAI-compatible endpoint can be used.

## Start

```powershell
docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml -f docker-compose.onlyoffice.yml -f docker-compose.postgres-local.yml -f docker-compose.ai-file-bot.yml up -d --build ai-file-bot
```

## Usage

Reply under a file message:

```text
@filebot analyze this file and summarize the key points
```

Or mention the bot shortly after an attachment in the same channel:

```text
@filebot analyze the latest attachment
```

The thread reply method is more reliable because the bot can directly locate the file in that thread.
