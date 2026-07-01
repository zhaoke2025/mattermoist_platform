# Mattermost 协作平台 Docker 部署

本仓库基于官方 Mattermost Docker 部署方案扩展，当前 `custom-platform` 分支已集成：

- Mattermost 聊天、文件、频道、@提醒
- ONLYOFFICE Docs 在线预览和协同编辑文档
- Mattermost Agents 接入 OpenAI-compatible 模型
- 自定义 `filebot` 附件内容分析 Bot
- Postgres 本地端口映射，便于 Navicat 等工具连接

本项目的中文部署和维护说明见：[docs/platform-deployment.md](docs/platform-deployment.md)。

---

# Mattermost Docker
[![ShellCheck](https://github.com/mattermost/docker/actions/workflows/shellcheck.yml/badge.svg)](https://github.com/mattermost/docker/actions/workflows/shellcheck.yml)
[![Docker Test](https://github.com/mattermost/docker/actions/workflows/docker-test.yml/badge.svg)](https://github.com/mattermost/docker/actions/workflows/docker-test.yml)

The official Docker deployment solution for Mattermost.

## Install & Usage

Refer to the [Mattermost Docker deployment guide](https://docs.mattermost.com/deployment-guide/server/deploy-containers.html) for instructions on how to install and use this Docker image.

## Contribute
PRs are welcome, refer to our [contributing guide](https://developers.mattermost.com/contribute/getting-started/) for an overview of the Mattermost contribution process.

## Upgrading from `mattermost-docker`

This repository replaces the [deprecated mattermost-docker repository](https://github.com/mattermost/mattermost-docker). For an in-depth guide to upgrading, please refer to [this document](https://github.com/mattermost/docker/blob/main/scripts/UPGRADE.md).
