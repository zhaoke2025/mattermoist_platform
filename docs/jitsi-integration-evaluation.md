# Mattermost 接入 Jitsi Meet 评估

本文档对应 ZZJ-23。DocSpace 阶段已完成，Jitsi 部署按本文结论执行；Linear 状态由项目负责人确认验收后另行更新。

## 结论

MVP 建议采用：

- 在现有生产服务器上以独立 Compose 项目部署 Jitsi Meet，使用独立域名 `https://meet.rongsunai.com`。
- Mattermost 安装社区维护的 Jitsi 插件。
- 第一阶段使用“新窗口打开会议”，不启用实验性的嵌入浮窗。
- 会议房间名称使用随机值或 UUID，不直接使用可猜测的频道名。
- 公网业务会议不使用公共 `meet.jit.si`，它只适合临时连通性验证。

在兼容性测试通过前，不把该插件视为生产可用。插件是社区维护的 Beta 项目，不由 Mattermost 官方提供支持。

## 方案对比

| 方案 | 优点 | 限制 | 结论 |
| --- | --- | --- | --- |
| Mattermost Calls | 已安装，入口原生，适合语音和屏幕共享 | 当前目标包含完整视频会议能力 | 保留，不替代 Jitsi 验证 |
| 公共 `meet.jit.si` | 无需部署，验证快 | 数据边界、可用性和会议策略不可控 | 只做临时测试 |
| 自建 Jitsi + Mattermost 插件 | 支持摄像头、会议链接和独立管理 | 需要服务器、域名、HTTPS及插件兼容性验证 | MVP 推荐 |

## 依赖条件

- 独立服务器或明确隔离的资源。
- 独立域名和有效 HTTPS 证书；摄像头和麦克风访问依赖安全上下文。
- 防火墙至少开放 `80/TCP`、`443/TCP` 和 `10000/UDP`。
- 使用 Jitsi 官方稳定版，而不是源码主分支或不固定版本。
- Mattermost 系统管理员可以手动上传插件包。
- 上线前明确访客、主持人和会议创建权限策略。

如果与其他服务同机，必须先检查端口冲突。当前 Mattermost Calls 已使用自己的媒体端口，Jitsi 不能未经规划直接复用。

## 已核实的部署拓扑（2026-08-06）

- 服务器：`118.178.125.202`，现有 Mattermost 11.9.0 和 DocSpace 3.7.2 保持不变。
- Jitsi：官方 Docker 稳定版 `stable-10978`，目录 `/srv/jitsi-meet`，持久化目录 `/srv/jitsi-meet-cfg`。
- Web：容器 HTTP 仅绑定 `127.0.0.1:8000`，由现有反向代理通过 `meet.rongsunai.com` 提供 HTTPS。
- 媒体：JVB 使用 `10000/UDP`，不复用 Mattermost Calls 的媒体端口。
- 身份策略：启用内部主持人认证和访客加入；访客可以加入已由主持人建立的会议，但不能自行创建会议。
- 回滚：停止 `/srv/jitsi-meet` Compose 项目并移除 `meet.rongsunai.com` 反向代理配置，Mattermost 和 DocSpace 不受影响。

服务器资源核对结果为 8 核 CPU、29 GiB 内存、根分区约 54 GiB 可用，满足小规模 MVP 验证。上线前仍需确认 DNS 已解析到该服务器、证书包含 `meet.rongsunai.com`，并同时在主机防火墙和云安全组开放 `10000/UDP`。

## 插件选择和配置

候选插件：

```text
mattermost-community/mattermost-plugin-jitsi
```

当前评估基线为插件 `v2.1.0`，其最低 Mattermost Server 版本为 5.2.0。插件包 SHA-256 为 `73b97d2f3411440b44886d37b99827f55f0da30141c77b3ec62b8fc2e0bd1de4`。

第一阶段配置：

- Jitsi Server URL：自建 Jitsi 的 HTTPS 地址。
- Meeting name：UUID 或随机名称。
- Meeting link：新窗口打开。
- Embedded mode：关闭。
- JWT：先在受控测试环境验证基础连通；生产外部会议前必须完成身份和访客策略验证。

不在代码库、插件配置截图或聊天消息中暴露 JWT 密钥。

## 执行记录（2026-08-06）

- Jitsi `stable-10978` 的 Web、Prosody、Jicofo 和 JVB 容器已启动，Jicofo 已识别 JVB。
- `meet.rongsunai.com` 的反向代理已加入现有 `onlyoffice-proxy`；服务器本地按 SNI 验证首页和 `config.js` 正常，DocSpace 与 Mattermost 原入口均返回 200。
- 主机防火墙已开放 `10000/UDP`；云安全组仍需以控制台规则为准。
- Mattermost 已安装并启用 Jitsi 插件 `v2.1.0`，配置为自建域名、UUID 房间名、新窗口打开及关闭 JWT。
- 插件安装时临时启用上传，完成后已恢复为禁止上传。
- 公网验收待 `meet.rongsunai.com` DNS 生效并为现有证书增加该域名后执行。

## 验收步骤

| 编号 | 操作 | 预期结果 |
| --- | --- | --- |
| J01 | 管理员手动上传并启用插件 | 插件成功启用，Mattermost 无异常日志 |
| J02 | 配置自建 Jitsi HTTPS 地址 | 配置保存，浏览器无证书错误 |
| J03 | 在测试频道执行 `/jitsi` | 返回不可猜测的会议链接 |
| J04 | 点击频道视频入口 | 在新窗口打开同一场会议 |
| J05 | 两个内部账号加入 | 双方摄像头、麦克风和音频正常 |
| J06 | 执行屏幕共享 | 另一参与者能看到共享内容 |
| J07 | 外部浏览器加入 | 行为符合已设定的访客和主持人策略 |
| J08 | 无权限用户尝试创建或管理会议 | 被策略正确限制 |
| J09 | 结束会议后检查日志 | Mattermost 和 Jitsi 无持续错误 |
| J10 | 再次验证 Mattermost Calls | 原有 Calls 插件仍能正常使用 |

还应分别验证 Chrome、Edge 和一台手机浏览器；网络条件允许时测试两名异地用户。

## 风险和退出条件

- 插件与 Mattermost 11.9 不兼容：停止上线，保留纯 Jitsi 链接方案或评估替代插件。
- 嵌入模式出现跨域、权限或界面问题：继续使用独立窗口，不在 MVP 中修补嵌入模式。
- 未完成会议身份和访客策略：只允许内网或受控测试，不开放外部业务会议。
- 音视频受防火墙或 NAT 影响：先修正 `PUBLIC_URL`、UDP 端口和网络映射，再判断插件问题。
- 社区插件停止维护或出现未修复安全问题：停止升级推广并重新评估集成方式。

## 输出物

部署验证时需保留：

- Jitsi 和插件的固定版本、下载地址与校验值。
- 域名、端口和反向代理配置，不包含密钥。
- J01 至 J10 的结果和证据。
- 已知限制、回滚方法和负责人。
