# Auto_Bangumi 项目约定

## 启动方式

始终从 `backend/` 目录启动后端：

```bash
cd backend && python src/main.py
```

`config/` 目录只有一处：`backend/config/config_dev.json`。不允许在项目根目录创建第二个 `config/`。

## Python 依赖

Python 3.13 环境下，bcrypt 必须 < 5.0（passlib 1.7.4 不兼容 bcrypt 5.x），否则 `first_run()` 创建默认用户时报 `password cannot be longer than 72 bytes`。

```bash
pip install "bcrypt<5"
```
