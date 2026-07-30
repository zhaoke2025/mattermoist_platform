# Mattermost 协作平台部署说明

本文档描述 `custom-platform` 分支的本地启动、验证、维护和后续部署注意事项。

## 当前能力

当前平台已经完成四个阶段：

1. Mattermost 原生聊天、频道、私聊、文件、@提醒。
2. Mattermost Agents 接入 OpenAI-compatible 模型，例如 DeepSeek。
3. ONLYOFFICE Docs 集成，实现聊天内文档预览和协同编辑。
4. 自定义 `filebot`，支持读取附件内容并调用大模型分析。

## 主要服务

| 服务 | 说明 | 默认访问 |
| --- | --- | --- |
| Mattermost | 协作聊天平台 | `MM_SERVICESETTINGS_SITEURL` |
| Postgres | Mattermost 数据库 | 容器内 `postgres:5432` |
| ONLYOFFICE Docs | 在线文档编辑服务 | `http://宿主机IP:8081` |
| ai-file-bot | 附件内容分析 Bot | 无页面入口 |

## 环境变量

首次部署时复制模板：

```powershell
cp env.example .env
```

重点检查以下变量：

```env
MM_SERVICESETTINGS_SITEURL=http://你的访问IP或域名:8065
POSTGRES_PASSWORD=修改为强密码
ONLYOFFICE_JWT_SECRET=修改为长随机字符串
AI_FILE_BOT_MATTERMOST_TOKEN=填入 Mattermost bot token
AI_FILE_BOT_OPENAI_BASE_URL=https://api.deepseek.com/v1
AI_FILE_BOT_OPENAI_API_KEY=填入大模型 API Key
AI_FILE_BOT_OPENAI_MODEL=deepseek-chat
```

注意：`.env` 含真实密钥，不要提交到 Git。

## 本地启动

启动整套服务：

```powershell
docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml -f docker-compose.onlyoffice.yml -f docker-compose.postgres-local.yml -f docker-compose.ai-file-bot.yml up -d
```

如果修改了 `ai-file-bot` 代码，单独重建 Bot：

```powershell
docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml -f docker-compose.onlyoffice.yml -f docker-compose.postgres-local.yml -f docker-compose.ai-file-bot.yml up -d --build ai-file-bot
```

停止整套服务：

```powershell
docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml -f docker-compose.onlyoffice.yml -f docker-compose.postgres-local.yml -f docker-compose.ai-file-bot.yml down
```

查看容器状态：

```powershell
docker ps
```

## 访问地址

浏览器访问：

```text
http://你的访问IP或域名:8065
```

本地测试时也建议使用 `.env` 中 `MM_SERVICESETTINGS_SITEURL` 配置的地址。不要一会儿用 `localhost`，一会儿用局域网 IP，否则 Agents、ONLYOFFICE、邀请链接可能出现地址不一致或 CORS 问题。

## Postgres 连接

如果启用了 `docker-compose.postgres-local.yml`，可以用 Navicat 等工具连接：

```text
Host: localhost
Port: 5432
Database: mattermost
User: mmuser
Password: 查看 .env 中 POSTGRES_PASSWORD
```

如果端口冲突，修改 `.env`：

```env
POSTGRES_LOCAL_PORT=5433
```

然后重启服务。

## ONLYOFFICE 验证

1. 在 Mattermost 频道上传 `.docx`、`.xlsx` 或 `.pptx` 文件。
2. 点击文件更多操作。
3. 选择 `Open file in ONLYOFFICE`。
4. 能打开编辑器并保存回 Mattermost，说明集成正常。

ONLYOFFICE 插件配置中 JWT Secret 必须和 `.env` 的 `ONLYOFFICE_JWT_SECRET` 一致。

## Agents 验证

1. 使用 `MM_SERVICESETTINGS_SITEURL` 对应地址访问 Mattermost。
2. 打开右侧 Agents 面板。
3. 选择 DeepSeek 或其他配置好的 agent。
4. 使用频道总结功能验证能读取频道上下文。

如果出现 CORS 错误，通常是浏览器访问地址和 `MM_SERVICESETTINGS_SITEURL` 不一致。

## filebot 验证

查看 Bot 日志：

```powershell
docker logs --tail 80 docker-ai-file-bot-1
```

正常日志示例：

```text
connected as @filebot
polling mentions for @filebot
```

推荐测试方式：

1. 在频道上传一个 PDF 或 DOCX。
2. 点击文件消息下方的回复。
3. 在线程中发送：

```text
@filebot 分析这个文件，并总结重点
```

如果触发成功，日志中会出现类似：

```text
post xxx matched, files=[...]
```

## 备份建议

至少备份以下目录和文件：

```text
.env
volumes/db/var/lib/postgresql/data
volumes/app/mattermost/config
volumes/app/mattermost/data
volumes/app/mattermost/plugins
volumes/onlyoffice/DocumentServer/data
volumes/onlyoffice/DocumentServer/lib
volumes/onlyoffice/DocumentServer/db
```

建议同时做数据库逻辑备份：

```powershell
docker exec docker-postgres-1 pg_dump -U mmuser mattermost > mattermost_backup.sql
```

恢复前必须先确认 Mattermost 和 Postgres 版本兼容。

## 服务器部署注意事项

上线服务器时重点处理：

1. 使用正式域名。
2. 配置 HTTPS。
3. 修改 `MM_SERVICESETTINGS_SITEURL` 为正式访问地址。
4. 配置 SMTP 邮件，确保邀请链接可用。
5. 修改所有默认密码和 JWT Secret。
6. 固定数据卷目录，并建立定期备份。
7. 不建议对公网暴露 Postgres 端口。

## 后续阶段

后续可以继续扩展：

- ONLYOFFICE DocSpace：当前优先阶段。参见 [职责边界](docspace-boundary.md)、[部署准备](docspace-deployment.md)、[频道与房间映射](docspace-room-mapping.md)和[外部协作验收](docspace-acceptance.md)。
- Jitsi Meet：DocSpace 后的下一阶段，参见 [接入评估](jitsi-integration-evaluation.md)。
- OCR：暂缓。后续让 `filebot` 支持扫描版 PDF 和图片文字识别。
- 统一平台 Bot：整合附件分析、会议创建、DocSpace 房间创建和通知。
