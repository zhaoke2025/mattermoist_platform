# DocSpace 与现有协作组件边界

本文档用于明确 Mattermost、ONLYOFFICE Docs 和 ONLYOFFICE DocSpace 的职责边界，并作为后续部署 DocSpace、验证外部协作和设计频道映射的依据。

## 结论

- Mattermost 继续作为统一沟通和协作入口。
- 现有 ONLYOFFICE Docs 继续作为 Mattermost 附件的在线编辑引擎。
- DocSpace 作为独立文档空间，保存需要长期管理、按房间组织或提供给外部人员访问的正式资料。
- 第一阶段不开发文件自动同步、成员自动同步或自定义 Mattermost 插件，先通过频道置顶链接关联 DocSpace 房间。

三者不是互相替换关系：

| 组件 | 核心职责 | 是否保存业务文档 | 典型入口 |
| --- | --- | --- | --- |
| Mattermost | 沟通、讨论、通知和工作入口 | 保存聊天附件 | 频道、私聊、线程 |
| ONLYOFFICE Docs | 打开和协同编辑 Mattermost 附件 | 不作为独立文档空间 | Mattermost 附件菜单 |
| ONLYOFFICE DocSpace | 房间化文档管理、权限控制和外部协作 | 保存正式文档 | 独立 DocSpace 页面 |

## 文档归属规则

### 放在 Mattermost

- 为讨论临时上传的附件。
- 需要结合聊天上下文查看的文件。
- 只在当前频道短期使用的草稿。
- 通过现有 ONLYOFFICE 插件直接编辑并保存回消息的文件。

### 放在 DocSpace

- 项目正式交付物和持续维护的文档。
- 需要按项目、客户或供应商建立资料室的文件。
- 需要独立于聊天记录进行分类和长期管理的文件。
- 需要邀请外部人员访问、编辑、评论或审阅的文件。
- 需要房间级权限和分享链接的文件。

### 不自动复制

第一阶段不在 Mattermost 与 DocSpace 之间自动复制文件，避免产生两个无法判断哪个是最新版的副本。

需要把聊天附件转为正式资料时，由用户将最终版本上传到对应 DocSpace 房间，并在 Mattermost 线程中发布房间或文件链接。

## 使用场景

### 场景一：聊天中快速协同编辑

1. 用户在 Mattermost 频道上传 DOCX、XLSX 或 PPTX。
2. 用户通过现有 ONLYOFFICE 插件打开附件。
3. 编辑结果保存回 Mattermost 附件。

该场景不进入 DocSpace。

### 场景二：内部项目文档空间

1. 在 DocSpace 创建项目协作房间。
2. 将项目方案、会议材料和交付文档放入房间。
3. 在 Mattermost 项目频道置顶 DocSpace 房间链接。
4. 讨论和通知留在 Mattermost，正式文档在 DocSpace 维护。

### 场景三：客户或供应商资料室

1. 在 DocSpace 创建独立外部协作房间。
2. 按需要授予查看、审阅、评论或编辑权限。
3. 将分享链接发送到对应 Mattermost 频道。
4. 外部人员通过 DocSpace 访问指定资料，不加入内部 Mattermost 团队。

### 场景四：聊天附件转正式资料

1. 团队先在 Mattermost 线程中讨论并修改附件。
2. 文件确认后，由负责人上传最终版本到 DocSpace。
3. 在线程中回复 DocSpace 文件链接，说明该链接是后续维护入口。

## Mattermost 与 DocSpace 的第一阶段关系

第一阶段使用人工维护的轻量映射：

- 一个 Mattermost 频道可以关联一个主要 DocSpace 房间。
- 没有正式文档空间需求的频道不强制创建房间。
- 房间链接放在频道头部、书签或置顶消息中。
- 房间成员和 Mattermost 频道成员分别维护，不假设权限天然一致。
- 房间建议使用“团队或项目-用途”的命名方式。

自动创建房间、成员同步、权限同步、文件通知和 Bot 操作属于后续增强，不作为 DocSpace 首次部署的阻塞项。

## 第一阶段不做的内容

- Mattermost 与 DocSpace 文件双向同步。
- Mattermost 用户与 DocSpace 用户自动同步。
- Mattermost 频道成员与 DocSpace 房间成员自动同步。
- 在 Mattermost 内嵌完整 DocSpace 页面。
- 在 ONLYOFFICE 编辑器中嵌入 Jitsi。
- 将现有 Mattermost 附件批量迁移到 DocSpace。

## 部署前置条件

DocSpace 应与现有 ONLYOFFICE Docs 隔离部署，并使用独立的数据目录和访问地址。

官方 DocSpace Docker 部署最低需要 6 核 CPU、12 GB 内存、40 GB 可用空间和 6 GB Swap，推荐 8 核 CPU、16 GB 内存。当前本地机器不适合与现有 Mattermost 服务同时承载 DocSpace，部署前应准备独立服务器或完成硬件扩容。

建议的正式访问方式：

```text
Mattermost: https://chat.example.com
ONLYOFFICE Docs: 仅作为 Mattermost 编辑服务
DocSpace: https://docs.example.com
```

DocSpace 部署完成后，先验证原生房间和权限能力，再开始设计自动映射。

## 后续执行顺序

1. 部署独立 DocSpace 服务。
2. 验证管理员登录、房间创建、文档上传和数据持久化。
3. 验证外部协作房间、分享链接和权限控制。
4. 根据实际使用结果设计 Mattermost 频道与 DocSpace 房间映射。

## 参考资料

- [ONLYOFFICE DocSpace Docker 部署](https://helpcenter.onlyoffice.com/docspace/installation/docspace-community-running-docker.aspx)
- [ONLYOFFICE DocSpace 项目说明](https://github.com/ONLYOFFICE/docspace)
