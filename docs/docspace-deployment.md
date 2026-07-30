# ONLYOFFICE DocSpace 部署准备

本文档对应 DocSpace 部署阶段。服务器到位前完成方案、检查项和验收口径；服务器到位后再执行安装和真实验收。

配套文档：

- [DocSpace 与现有 ONLYOFFICE Docs 的职责边界](docspace-boundary.md)
- [Mattermost 频道与 DocSpace 房间映射设计](docspace-room-mapping.md)
- [DocSpace 初始化、外部协作与备份恢复验收](docspace-acceptance.md)

## 当前结论

- DocSpace 使用独立服务器，不与现有 Mattermost 或 `ibiyer-api` 混合部署。
- 正式访问地址使用独立域名，例如 `https://docs.example.com`。
- DocSpace 数据必须落在持久化数据盘，并建立独立备份。
- 第一阶段先验证 DocSpace 原生能力，不开发 Mattermost 自动同步插件。
- 当前官方 Community Docker 说明明确标注为开发、测试构建，不作为正式生产版本。MVP 可以用它完成技术验证，正式对外使用前必须确认 Community 或 Enterprise 版本和授权方案。

## 已核对的官方部署结构

以官方 `DocSpace-buildtools` 的 `v3.7.2-server` 标签为当前准备基线。Community Docker 目录包含以下服务：

| 服务 | 用途 |
| --- | --- |
| `onlyoffice-docspace` | DocSpace 应用服务 |
| `onlyoffice-document-server` | 在线文档编辑器 |
| `onlyoffice-mysql-server` | DocSpace 数据库 |
| `onlyoffice-opensearch` | 文档搜索 |

正式部署时应再次检查官方最新稳定标签，并固定源码标签和镜像摘要，不能长期使用不可追踪的 `latest`。

## 服务器要求

官方 Docker 测试构建最低要求：

- amd64 Linux。
- 6 核 CPU，推荐 8 核。
- 12 GB 内存，推荐 16 GB。
- 40 GB 可用磁盘。
- 6 GB Swap。
- Docker Engine 和 Docker Compose 插件。

本项目建议服务器配置：

- 8 核 CPU。
- 32 GB 内存。
- 100 GB 系统盘。
- 200 GB 以上 SSD 数据盘，建议 500 GB。
- 8 GB Swap。
- 固定公网 IP。
- 独立备份目标。

## 服务器预检

服务器到位后先上传并执行：

```bash
chmod +x scripts/check-docspace-host.sh
DOCSPACE_CHECK_PATH=/srv/docspace ./scripts/check-docspace-host.sh
```

只有所有硬性检查通过后才能开始安装。端口被占用会显示警告，需要先确认现有服务和反向代理方案。

## 目录规划

建议使用：

```text
/opt/docspace/                 部署配置和固定版本源码
/srv/docspace/                 DocSpace 持久化数据
/mnt/docspace-backup/          独立备份挂载点
```

Docker 命名卷默认位于 Docker Root Dir。正式启动前必须确认 Docker Root Dir 位于数据盘，或者使用官方 `VOLUMES_DIR` 将 `app_data`、`mysql_data`、`os_data`、日志和字体目录落到 `/srv/docspace`。

备份目录不能只放在同一块数据盘上；`/mnt/docspace-backup` 应指向 NAS、对象存储网关或其他独立设备。

## 域名和网络

部署前准备：

- DocSpace 域名，例如 `docs.example.com`。
- 域名解析到服务器公网 IP。
- 防火墙开放 `80/TCP` 和 `443/TCP`。
- 生产访问统一使用 HTTPS。
- MySQL 和 OpenSearch 不允许暴露到公网。

若使用 Let's Encrypt，必须先确认域名解析已生效。证书申请失败时不要反复重试，避免触发签发频率限制。

## 配置和密钥

官方 Community Docker 配置包含示例密码，部署时必须全部替换：

- `APP_CORE_MACHINEKEY`
- `DOCUMENT_SERVER_JWT_SECRET`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- 其他启用组件的账号和密码

`.env` 只保存在服务器，权限设置为 `600`，不得提交到 Git。

同时设置：

```text
APP_CORE_BASE_DOMAIN=实际域名
APP_URL_PORTAL=https://实际域名/
VOLUMES_DIR=/srv/docspace/volumes
```

最终变量名和取值应以部署时选定的官方固定版本为准。

## 部署步骤

服务器到位后的执行顺序：

1. 运行主机预检脚本。
2. 确认数据盘挂载、Swap、DNS 和防火墙。
3. 安装 Docker Engine 和 Docker Compose 插件。
4. 获取官方固定版本的 `DocSpace-buildtools`。
5. 复制并修改官方环境变量文件，生成所有随机密钥。
6. 先执行 Compose 配置校验，不启动服务。
7. 拉取固定版本镜像并记录镜像摘要。
8. 启动 DocSpace。
9. 等待 DocSpace、MySQL、OpenSearch 和 Document Server 全部健康。
10. 创建管理员并执行功能验收。

服务器实际信息未确认前，不在文档中保存 IP、密码、Token 或私钥。

## 验收清单

部署完成必须验证：

- HTTPS 页面可访问且证书有效。
- 管理员可以登录。
- 可以创建协作房间。
- 可以上传 DOCX、XLSX、PPTX 和 PDF。
- 可以在线打开、编辑并保存文档。
- 容器重启后管理员、房间和文档仍然存在。
- MySQL 和 OpenSearch 没有暴露到公网。
- 备份任务可以生成可恢复的备份。
- Mattermost 现有 ONLYOFFICE Docs 和 filebot 不受影响。

## 回滚原则

- 升级前备份数据库、应用数据和部署配置。
- 保留上一个可用的源码标签、环境变量副本和镜像摘要。
- 回滚时恢复成套数据库和文件数据，不能只回滚容器镜像。
- 禁止使用 `docker compose down -v`，避免删除命名卷。
- 没有完成一次恢复演练前，不把备份任务视为验收通过。

## 尚需服务器的信息

服务器交付后补充：

- 公网 IP 和内网 IP。
- 实际 CPU、内存、Swap。
- 系统盘和数据盘挂载点。
- Docker Root Dir。
- 最终域名。
- 防火墙和安全组规则。
- Community 测试版或 Enterprise 生产版选择。

## 官方资料

- [ONLYOFFICE DocSpace Docker 部署说明](https://helpcenter.onlyoffice.com/docspace/installation/docspace-community-running-docker.aspx)
- [ONLYOFFICE DocSpace buildtools](https://github.com/ONLYOFFICE/DocSpace-buildtools)
- [ONLYOFFICE DocSpace 下载与生产版本](https://www.onlyoffice.com/download)
