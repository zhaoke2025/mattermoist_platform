# Mattermost 协作平台部署说明

本文档描述 `custom-platform` 分支的本地启停、生产部署、验证、备份和恢复流程。

## 当前能力

当前平台已集成：

1. Mattermost 原生聊天、频道、私聊、文件、@提醒。
2. Mattermost Agents 接入 OpenAI-compatible 模型，例如 DeepSeek。
3. ONLYOFFICE Docs 集成，实现聊天内文档预览和协同编辑。
4. 自定义 `filebot`，支持附件分析、云端 OCR、PaddleOCR 自动兜底、Jitsi 会议和 DocSpace 房间命令。

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
AI_FILE_BOT_OCR_API_KEY=填入百炼 API Key
AI_FILE_BOT_DOCSPACE_BASE_URL=https://docs.example.com
AI_FILE_BOT_DOCSPACE_API_KEY=填入 DocSpace API Key
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

停止命令默认保留数据卷；不要添加 `-v`。如需重新启动，先确认 Docker Desktop 已运行，再执行启动命令。排查时使用：

```powershell
docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml -f docker-compose.onlyoffice.yml -f docker-compose.postgres-local.yml -f docker-compose.ai-file-bot.yml ps
docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml -f docker-compose.onlyoffice.yml -f docker-compose.postgres-local.yml -f docker-compose.ai-file-bot.yml logs --tail 100 mattermost ai-file-bot
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

## 生产服务器部署

生产环境使用固定版本镜像、外部 ONLYOFFICE 网络和持久卷。首次部署前先创建数据库卷与网络：

```bash
docker volume create mattermost_mattermost_postgres_data
docker network create onlyoffice
```

检查最终配置，确认输出中没有空的必填密钥：

```bash
docker compose -f docker-compose.production.yml --profile ai-file-bot config
```

启动或更新服务：

```bash
docker compose -f docker-compose.production.yml --profile ai-file-bot up -d --build
docker compose -f docker-compose.production.yml --profile ai-file-bot ps
```

生产域名必须使用 HTTPS，并确保：

- `MM_SERVICESETTINGS_SITEURL` 为外部正式地址，例如 `https://chat.example.com`。
- 反向代理转发到 Mattermost `8065`，保留 WebSocket 升级头。
- 证书使用 `scripts/issue-certificate.sh` 申请，或由服务器现有网关统一管理。
- 续期后重新加载反向代理，并检查证书到期时间。
- Postgres、Mattermost 内部端口和 DocSpace API Key 不对公网暴露。

## SMTP

在 `.env` 中配置 `MM_EMAILSETTINGS_*`。推荐端口 `587` 和 `STARTTLS`，保持 `MM_EMAILSETTINGS_SKIPSERVERCERTIFICATEVERIFICATION=false`。先将 `MM_EMAILSETTINGS_SENDEMAILNOTIFICATIONS=false`，在系统控制台发送测试邮件成功后再改为 `true` 并重建 Mattermost：

```bash
docker compose -f docker-compose.production.yml up -d --force-recreate mattermost
```

SMTP 密码只保存在服务器 `.env` 或密钥管理系统，不写入仓库、聊天消息和运维截图。若暂时没有 SMTP 服务，密码找回和邮件通知不能作为已验收功能。

## 备份

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

生产服务器执行：

```bash
chmod +x scripts/backup-production.sh
./scripts/backup-production.sh /mnt/backup/mattermost
```

脚本会短暂停止 Mattermost 和 `ai-file-bot`，生成 PostgreSQL 自定义格式备份、Mattermost 文件、Bot 映射、`.env`、证书和 SHA-256 校验文件，并在结束或异常退出时重新启动服务。备份目录必须再同步到独立磁盘、NAS 或对象存储。

DocSpace、Jitsi 和 ONLYOFFICE 若由独立 Compose 项目部署，必须分别按其部署文档备份；本脚本不假定它们与 Mattermost 共用数据库。

## 恢复演练

恢复操作具有破坏性，只能先在隔离服务器执行：

1. 使用与备份时相同的 Mattermost、Postgres 和插件版本创建空环境。
2. 执行 `sha256sum -c SHA256SUMS`，校验所有备份文件。
3. 停止 Mattermost 和 `ai-file-bot`。
4. 使用 `pg_restore --clean --if-exists` 将 `mattermost.dump` 恢复到空数据库。
5. 将 `mattermost-files.tar.gz` 恢复到 Mattermost 对应数据卷，将 Bot 数据恢复到 `/app/data`。
6. 恢复服务器 `.env`，核对域名、密码、JWT、模型和 DocSpace 密钥后启动服务。
7. 验证登录、频道消息、附件下载、ONLYOFFICE 编辑、OCR 云端与兜底、会议创建、DocSpace 房间映射及成员同步。
8. 记录恢复耗时、数据时间点和异常；未完成一次隔离恢复演练前，不将备份项标记为验收通过。

## 上线检查清单

上线服务器时重点处理：

1. 使用正式域名。
2. 配置 HTTPS。
3. 修改 `MM_SERVICESETTINGS_SITEURL` 为正式访问地址。
4. 配置并实际发送 SMTP 测试邮件，确认邀请和密码找回可用。
5. 修改所有默认密码和 JWT Secret。
6. 固定数据卷目录，并建立定期备份。
7. 不建议对公网暴露 Postgres 端口。

相关验收说明：DocSpace 参见 [部署准备](docspace-deployment.md)、[频道与房间映射](docspace-room-mapping.md)和[外部协作验收](docspace-acceptance.md)；Jitsi 参见 [接入评估](jitsi-integration-evaluation.md)。
