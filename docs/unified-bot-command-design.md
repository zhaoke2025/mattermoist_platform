# 统一平台 Bot 命令体系设计

本文档对应 Linear `ZZJ-33`，用于指导附件分析、会议创建和 DocSpace 房间自动映射能力接入统一 Bot。

## 1. 目标与范围

统一用户入口、命令格式、权限校验、错误提示和审计字段，避免用户分别记忆 `@filebot`、`@deepseek`、`/jitsi` 和 DocSpace 管理入口。

MVP 只统一命令入口和响应规范，不重写现有 OCR、LLM、Jitsi 或 DocSpace 服务。

## 2. 当前能力

| 能力 | 当前入口 | 当前实现 | 统一后的适配方式 |
| --- | --- | --- | --- |
| 附件分析 | `@filebot` | filebot 轮询提及，提取附件后调用 LLM | 复用现有提取、OCR 和总结逻辑 |
| 通用 AI | `@deepseek` | Mattermost Agents 插件 | 保留独立助手，不承担确定性命令路由 |
| 视频会议 | `/jitsi` | Mattermost Jitsi 插件 | 统一 Bot 校验参数后调用会议适配器 |
| DocSpace | 频道固定入口、人工建房 | 人工登记 `channel_id` 与 `room_id` | 通过 DocSpace API 创建房间并登记映射 |

## 3. Bot 名称和调用格式

- 用户名：`assistant`
- 显示名：`平台助手`
- 频道调用：`@assistant <domain> <action> [arguments]`
- 回复位置：默认回复到触发消息所在话题。
- 命令和参数使用英文小写；Bot 的提示、结果和错误默认使用中文。

命令路由必须由确定性解析器完成，不允许大模型决定要执行哪个系统命令。自然语言只作为明确命令后的业务参数，例如附件分析要求或会议标题。

## 4. MVP 命令

### 4.1 帮助

```text
@assistant help
@assistant help file
@assistant help meeting
@assistant help docspace
```

### 4.2 附件分析

```text
@assistant file analyze
@assistant file analyze 请提取合同金额、甲乙方和截止日期
```

规则：

- 从当前话题获取附件；当前话题没有附件时，按现有 filebot 规则查找相邻消息。
- 每次最多处理 3 个附件。
- 支持现有办公文档、图片和扫描 PDF。
- 不改变“云端 OCR 主用、PaddleOCR 自动兜底”的实现。

### 4.3 创建会议

```text
@assistant meeting create 项目周会
@assistant meeting create 项目周会 --duration 60
```

规则：

- 会议房间名由服务端生成 UUID，不使用可猜测的频道名或标题。
- 标题只用于 Mattermost 展示，不直接作为 Jitsi 房间 ID。
- 成功后返回会议标题、入口、创建人和有效时间。
- MVP 在新窗口打开会议，不做嵌入式会议窗口。

### 4.4 DocSpace 房间

```text
@assistant docspace create OPC 项目资料
@assistant docspace link
@assistant docspace status
```

规则：

- `create` 创建当前频道的主 DocSpace 房间并登记映射。
- `link` 返回当前频道已登记的固定房间入口。
- `status` 返回映射状态、房间名称、负责人和权限申请方式。
- 映射唯一键使用 Mattermost `channel_id` 和 DocSpace `room_id`，不能只使用显示名称。
- 每个频道最多配置一个主房间；重复创建必须返回已有映射，不能创建重复房间。

## 5. 解析与路由

处理顺序：

1. 验证消息是否明确提及 `@assistant`。
2. 去掉提及并按空白字符解析 `domain` 和 `action`。
3. 校验命令、必填参数和选项。
4. 根据命令执行权限检查。
5. 生成以触发消息 ID 为幂等键的请求。
6. 调用对应适配器。
7. 在原话题返回统一格式结果并记录审计信息。

路由表：

| Domain | Action | 适配器 |
| --- | --- | --- |
| `help` | - | 静态帮助 |
| `file` | `analyze` | filebot 附件分析适配器 |
| `meeting` | `create` | Jitsi 会议适配器 |
| `docspace` | `create` | DocSpace 建房适配器 |
| `docspace` | `link` | 映射查询适配器 |
| `docspace` | `status` | 映射状态适配器 |

未知命令不得猜测执行，应返回帮助和最接近的合法示例。

## 6. 权限控制

| 命令 | 最低权限 | 额外限制 |
| --- | --- | --- |
| `help` | 已登录用户 | 无 |
| `file analyze` | 可读取当前频道和附件 | 私有频道内容不得发送到其他频道 |
| `meeting create` | 当前频道成员 | 可通过配置限制为指定角色或用户组 |
| `docspace link/status` | 当前频道成员 | 只返回当前频道映射 |
| `docspace create` | 频道管理员或配置的项目负责人 | 创建前二次确认，记录操作者 |

服务端 API Key、JWT 和 Bot Token 只能保存在环境变量或密钥服务中，不得出现在消息、日志或命令参数里。

## 7. 二次确认与幂等

- 查询和附件分析不需要二次确认。
- 创建 DocSpace 房间必须二次确认。
- 创建会议默认不需要确认，但同一触发消息只能创建一次。
- 使用 Mattermost 触发消息 ID 作为幂等键；重试时返回原结果。
- 外部服务成功但 Mattermost 回复失败时，重试只能补发回复，不能重复创建资源。

确认示例：

```text
即将为当前频道创建 DocSpace 房间“OPC 项目资料”。
请回复：@assistant confirm <request-id>
```

## 8. 响应格式

成功响应：

```text
### 执行成功
- 命令：docspace create
- 结果：已创建并绑定房间 OPC 项目资料
- 入口：https://docs.example.com/rooms/...
- 操作人：@username
- 请求 ID：<request-id>
```

失败响应：

```text
### 执行失败
- 错误码：BOT-PERMISSION-DENIED
- 原因：当前账号没有创建 DocSpace 房间的权限
- 建议：联系频道管理员或执行 @assistant help docspace
- 请求 ID：<request-id>
```

附件分析结果继续使用“简短结论 + 关键要点 + 信息不足说明”的现有格式。

## 9. 错误规范

| 错误码 | 含义 |
| --- | --- |
| `BOT-COMMAND-INVALID` | 命令或参数不合法 |
| `BOT-ATTACHMENT-NOT-FOUND` | 未找到可分析附件 |
| `BOT-FILE-UNSUPPORTED` | 文件格式不支持 |
| `BOT-PERMISSION-DENIED` | 权限不足 |
| `BOT-CONFIRMATION-REQUIRED` | 等待二次确认 |
| `BOT-UPSTREAM-TIMEOUT` | Jitsi、DocSpace、OCR 或 LLM 超时 |
| `BOT-UPSTREAM-UNAVAILABLE` | 外部服务不可用 |
| `BOT-CONFLICT` | 资源或映射已存在 |
| `BOT-INTERNAL-ERROR` | 未分类内部错误 |

用户消息不得包含堆栈、Token、内部主机地址或完整上游响应。详细异常只写服务端日志，并通过请求 ID 关联。

## 10. 审计字段

每次命令至少记录：

- `request_id`
- `command`
- `mattermost_user_id`
- `team_id`
- `channel_id`
- `root_post_id`
- `target_resource_id`
- `result`
- `error_code`
- `duration_ms`
- `created_at`

日志不得记录附件全文、模型 API Key、DocSpace Token 或 Jitsi JWT。

## 11. 兼容与迁移

- 第一阶段保留 `@filebot`、`@deepseek` 和 `/jitsi`，避免影响现有用户。
- `@assistant file analyze` 复用 filebot 能力，稳定后再提示用户迁移。
- `@deepseek` 继续作为开放式 AI 对话入口；统一 Bot 只处理明确的平台命令。
- 旧入口至少保留一个发布周期，确认无调用后再决定是否停用。

## 12. 后续任务边界

- `ZZJ-35`：实现 `file analyze` 路由并复用现有 filebot。
- `ZZJ-36`：实现 `meeting create`、权限和幂等处理。
- `ZZJ-37`：实现 DocSpace 建房、频道映射、通知和查询。

## 13. ZZJ-33 验收清单

- [x] 明确 Bot 名称和显示名。
- [x] 明确命令格式和 MVP 命令集合。
- [x] 明确权限控制和二次确认规则。
- [x] 明确错误码和用户提示格式。
- [x] 明确审计字段和敏感信息边界。
- [x] 明确现有能力的兼容与迁移策略。
- [x] 输出统一命令设计文档。
