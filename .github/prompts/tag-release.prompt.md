---
description: "根据 pyproject.toml 版本号打 beta tag → 推送 → 监听 CI → 路由器拉取新镜像重启"
agent: agent
tools: [terminal, web]
---
# 打 beta tag 发布流程

## 1. 读取版本号
从 `backend/pyproject.toml` 中提取当前版本号（`version` 字段），如 `3.2.4`。

## 2. 确认 tag
列出最近 5 个 tag 确认最新 beta 号。按 `pyproject.toml` 中的版本号打 `{version}-beta.{n+1}` tag。例如 `version = "3.2.4"` → `3.2.4-beta.1`（如果已有 `3.2.4-beta.1` 则递增为 `.2`）。

## 3. 推送 tag
执行 `git tag {tag}` → `git push origin {tag}`

## 4. 监听 CI
等待 5 秒后用 `gh run list` 获取最新 run ID，然后用 `gh run watch` 实时监听直到完成。

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

## 6. 验证
查看新容器日志确认启动正常，提示用户访问 `http://192.168.31.1:17892` 测试前端是否正常显示。
