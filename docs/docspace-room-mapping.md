# Mattermost 频道与 DocSpace 房间映射设计

本文档对应 ZZJ-30。目标是在不开发同步插件的前提下，让用户可以从 Mattermost 频道稳定进入对应的 DocSpace 文档空间。

## 版本说明

- 第一版（设计版）：确定频道与房间的职责边界、命名规则、登记字段和人工授权流程。
- 第二版（落地验收版）：基于正式 Mattermost、DocSpace 域名和普通用户账号完成真实映射及权限验证。

## 第二版结论

- Mattermost 是沟通入口，DocSpace 是正式文档空间。
- 一个频道可以配置一个“主 DocSpace 房间”，但不是所有频道都必须创建房间。
- 一个 DocSpace 房间默认只对应一个频道；确需跨频道共用时，由房间负责人确认。
- 当前不自动同步频道成员、DocSpace 成员和权限，也未配置单点登录。
- 房间入口以频道书签或频道置顶消息发布，不把文档重复上传到两个系统。

这种设计先解决“文档放哪里、用户从哪里进入”的问题，并避免两套成员权限自动同步带来的误授权。

## 房间命名

建议格式：

```text
[团队简称]-[频道或项目简称]-[用途]
```

示例：

```text
研发-协作平台-项目资料
市场-客户A-交付资料
```

名称用于识别，实际关联以 Mattermost `channel_id` 和 DocSpace `room_id` 为准，不能只依赖可修改的显示名称。

## 映射登记

每个映射至少登记以下字段：

| 字段 | 说明 |
| --- | --- |
| `team_id` | Mattermost 团队 ID |
| `channel_id` | Mattermost 频道 ID，唯一关联键 |
| `channel_name` | 频道显示名称，方便人工识别 |
| `room_id` | DocSpace 房间 ID |
| `room_name` | DocSpace 房间名称 |
| `room_url` | 固定房间入口 |
| `room_type` | 协作房间、公共房间等 |
| `owner` | 房间负责人 |
| `status` | 使用中、暂停或已归档 |
| `created_at` | 建立映射的时间 |

第一阶段可用受控表格登记。不要在 Git 中保存邀请链接、访问令牌或个人信息。

### 首个正式映射

| 字段 | 当前值 |
| --- | --- |
| `team_id` | 已在 Mattermost 正式环境建立，后续 Bot 接入时回填内部 ID |
| `channel_id` | 已在 Mattermost 正式环境建立，后续 Bot 接入时回填内部 ID |
| `channel_name` | `DocSpace文档协作` |
| `room_id` | `9` |
| `room_name` | `OPC-DocSpace-验收` |
| `room_url` | `https://docs.rongsunai.com/rooms/shared/9/filter?folder=9&page=1&sortby=DateAndTime&sortorder=descending` |
| `room_type` | 协作房间 |
| `owner` | DocSpace 管理员 |
| `status` | 使用中，入口及普通用户编辑权限已验证 |
| `created_at` | `2026-08-04` |
| `accepted_at` | `2026-08-05` |

Mattermost 已创建私有频道 `DocSpace文档协作`，并在频道标题中发布以下固定入口：

```text
本频道正式文档统一存放在 DocSpace：
房间：OPC-DocSpace-验收
入口：https://docs.rongsunai.com/rooms/shared/9/filter?folder=9&page=1&sortby=DateAndTime&sortorder=descending
权限申请：联系 DocSpace 房间管理员
```

上述地址是固定房间地址，不是有有效期的邀请链接；用户仍须在 DocSpace 中获得对应房间权限。

### 第二版验收结果

- 普通用户经邀请后可加入 Mattermost，并仅在被授权后看到私有频道。
- 普通用户从频道固定入口可进入 `OPC-DocSpace-验收` 房间。
- 普通用户在 DocSpace 中被授予编辑器权限，可打开、编辑并保存文档。
- Mattermost 与 DocSpace 目前使用独立账号和独立会话，跳转后未登录时进入 DocSpace 登录页属于预期行为。

## 权限规则

- Mattermost 频道成员不等于 DocSpace 房间成员。
- DocSpace 房间负责人负责邀请、调整权限和移除成员。
- 内部成员按最小权限授予查看或编辑角色。
- 外部人员只加入指定房间，不能因加入一个房间访问其他房间。
- 外部分享链接不得发布到公开频道；人员离场或项目结束后应立即撤销。
- 频道管理员负责入口是否可见，房间负责人负责入口背后的访问权限。

## 建立映射的流程

1. 频道负责人提出文档空间用途、成员范围和房间负责人。
2. DocSpace 管理员创建房间并设置初始权限。
3. 管理员取得房间 ID 和固定访问地址，写入映射登记。
4. 频道管理员把入口添加到频道书签或置顶消息。
5. 使用一个普通内部账号验证入口和权限。
6. 如有外部协作，再按外部协作验收清单验证。

置顶消息建议模板：

```text
本频道正式文档统一存放在 DocSpace：
房间：研发-协作平台-项目资料
入口：https://docs.example.com/rooms/...
负责人：姓名
权限申请：联系房间负责人
```

## 变更和归档

- 频道改名：更新登记中的显示名称，不新建房间。
- 房间改名或地址变化：同步更新频道入口和映射登记。
- 更换负责人：先完成 DocSpace 权限移交，再修改登记。
- 频道归档：移除频道入口，房间根据资料保留要求设为只读或归档。
- 删除房间：必须先确认备份、保留期限和映射状态，不直接删除。

## 后续自动化边界

后续 Bot 可以使用 DocSpace API Key 做服务端自动化：

- 查询房间：`GET /api/2.0/files/rooms`
- 创建房间：`POST /api/2.0/files/rooms`
- 邀请成员：`PUT /api/2.0/files/rooms/{roomId}/share`

自动化必须以 `channel_id` 查询映射，重复请求不能重复创建房间。API Key 只保存在服务端密钥配置中，不发送到 Mattermost 客户端。

第一阶段不实现自动建房、自动邀请、自动移除成员和双向文件同步。

## 验收标准

- 已明确频道和房间不是强制一一对应，而是每个频道最多配置一个主房间。
- 已确定房间命名和唯一关联键。
- 已明确权限不自动同步及双方负责人职责。
- 已确定频道书签或置顶消息为固定入口。
- 已形成可维护的映射字段和建立、变更、归档流程。
