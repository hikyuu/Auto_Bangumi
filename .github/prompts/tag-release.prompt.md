---
description: "根据 pyproject.toml 版本号打 beta tag → 推送 → 监听 CI → 路由器拉取新镜像重启"
agent: agent
tools: [vscode, execute, read, agent, search, todo]
---
# 打 beta tag 发布流程

## 1. 读取版本号
从 `backend/pyproject.toml` 中提取当前版本号（`version` 字段），如 `3.2.4`。

## 2. 确认 tag
列出最近 5 个 tag 确认最新 beta 号。按 `pyproject.toml` 中的版本号打 `{version}-beta.{n+1}` tag。例如 `version = "3.2.4"` → `3.2.4-beta.1`（如果已有 `3.2.4-beta.1` 则递增为 `.2`）。

## 3. 推送 tag
执行 `git tag {tag}` → `git push origin {tag}`

## 4. 监听 CI
所有 `gh` 命令必须指定 `--repo hikyuu/Auto_Bangumi`（本仓库是 fork，gh 默认指向上游 `EstrellaXD/Auto_Bangumi`，不指定会查不到 run）。
等待 5 秒后用 `gh run list --repo hikyuu/Auto_Bangumi` 获取最新 run ID，然后用 `gh run watch --repo hikyuu/Auto_Bangumi` 实时监听直到完成。
⚠️ `gh run watch` 会一直阻塞到 CI 完成，必须使用 **异步模式**（`mode: async`，不设 timeout）运行。
⚠️ `gh run watch` 启动后等**系统自动通知** completion 即可，不需要轮询。

## 5. 部署到路由器
CI 通过后 SSH 到路由器拉取新镜像并重启：
```bash
ssh root@192.168.31.1 "
  docker pull ghcr.io/hikyuu/auto_bangumi:latest &&
  cd /mnt/mmc0-4/docker/autoBangumi &&
  docker compose down --remove-orphans &&
  docker compose up -d
"
```

## 6. 等待健康检查
等待 60 秒让容器完成启动和健康检查，然后查询容器健康状态：
```bash
ssh root@192.168.31.1 "docker ps --filter name=AutoBangumi --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}'"
```
确认状态显示为 `(healthy)`。
