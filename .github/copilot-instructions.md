# Project Constraints

## Windows + Git Bash 注意事项

本项目在 Windows 环境下使用 Git Bash 开发。请注意以下约束：

### 禁止使用 `> nul` / `2> nul`

在 Git Bash 中，`> nul` 或 `2> nul` 会在**当前工作目录下创建一个空文件 `nul`**（因为 MSYS2 将其解析为普通文件名而非 Windows 设备名）。

**正确做法：**
- 丢弃标准输出 → `> /dev/null`
- 丢弃错误输出 → `2> /dev/null`
- 同时丢弃 → `&> /dev/null`

**错误❌（会生成 `nul` 文件）：**
```bash
some_command 2> nul
some_command > nul
```
