# AIName / 知名

AIName 是一个基于大语言模型的智能起名系统，支持人名、企业名和宠物名生成。系统会结合用户偏好、避用字、知识库资料和多轮反馈，生成带有出处、寓意和企业域名建议的命名方案。

AIName is an AI-powered naming system for personal names, company names, and pet names. It combines user preferences, excluded characters, knowledge-base references, and multi-turn feedback to create names with references, meanings, and domain suggestions.

## 项目亮点

- 一站式起名体验：登录、注册、起名、反馈、收藏、导出。
- 多场景支持：人名、企业名、宠物名采用不同提示词和长度规则。
- 企业知识库：支持用户私有知识库和平台公共知识库。
- 历史与收藏：自动保存生成记录，支持收藏、删除、重新生成和导出。
- 额度与统计：每日免费成功生成次数限制，失败不扣额度；管理员可查看 Token 消耗和调用统计。
- 管理员模块：查看、搜索、禁用用户，维护公共知识库。
- 友好异常处理：大模型繁忙、返回空结果或限流时，前端会给出明确提示。
- 多端适配：uni-app 前端适配 H5、移动端和小程序场景。

## 功能模块

### 用户端

- 邮箱验证码注册与登录
- JWT 身份认证
- 用户中心：修改用户名、邮箱、密码
- 查看登录记录和使用次数
- 注销账号
- 人名、企业名、宠物名生成
- 多轮反馈调整
- 起名历史与收藏
- 收藏方案导出：
  - 人名 / 宠物名：PDF 或 PNG 图片
  - 企业名：PDF 命名报告，包含名字、出处、寓意和域名状态

### 知识库

- 上传 PDF / TXT 文件
- 查看解析状态、启用状态、文件大小和向量片段数
- 私有知识库：仅当前用户企业起名时参考
- 公共知识库：管理员维护，所有用户企业起名时可参考
- 支持启用、停用和删除知识库文件

### 管理端

- 查看普通用户列表
- 搜索用户
- 禁用或恢复用户
- 查看 DeepSeek Token 消耗统计
- 查看模型调用明细
- 管理平台公共知识库

## 技术栈

### Backend

- FastAPI
- SQLAlchemy
- Alembic
- MySQL
- PostgreSQL checkpoint for LangGraph
- Redis
- LangChain / LangGraph
- DeepSeek
- Chroma
- Ollama Embeddings
- ReportLab / Pillow
- JWT
- FastAPI Mail

### Frontend

- Vue 3
- uni-app
- Composition API
- `uni.request`
- 响应式页面布局

## 项目结构

```text
AIName/
├── backend/
│   ├── alembic/          # 数据库迁移
│   ├── core/             # 认证、数据库、工作流、RAG 服务
│   ├── models/           # SQLAlchemy 模型
│   ├── repository/       # 数据访问层
│   ├── routers/          # FastAPI 路由
│   ├── schemas/          # Pydantic 请求与响应模型
│   ├── services/         # 额度控制、导出等服务
│   ├── settings/         # 配置
│   ├── main.py           # 后端入口
│   └── requirements.txt
├── frontend/
│   ├── pages/            # 页面
│   ├── utils/            # 请求封装
│   ├── config.js         # 后端地址
│   └── pages.json
├── .gitignore
└── README.md
```

## 本地运行

### 1. 后端环境

准备以下服务：

- Python
- MySQL
- PostgreSQL
- Redis
- Ollama，本地 Embedding 模型：`nomic-embed-text`
- DeepSeek API Key
- 邮箱 SMTP 服务

进入后端目录：

```bash
cd backend
pip install -r requirements.txt
```

复制示例环境变量文件，并按本地服务修改：

```bash
copy .env.example .env
```

Linux / macOS 可使用：

```bash
cp .env.example .env
```

常见配置项包括：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=ainame

PG_NAME=postgresql
PG_USER=postgres
PG_PWD=your-postgres-password
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DB_NAME=ainame

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0

JWT_SECRET_KEY=replace-with-a-strong-secret
DEEPSEEK_API_KEY=your-deepseek-api-key

HISTORY_RETENTION_DAYS=30
HISTORY_MAX_PER_USER=100
DAILY_FREE_GENERATIONS=3
```

执行数据库迁移：

```bash
alembic upgrade head
```

启动后端：

```bash
uvicorn main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

### 2. 创建管理员

先通过前端注册一个普通用户，然后在 `backend` 目录执行：

```bash
python create_admin.py admin@example.com
```

将 `admin@example.com` 替换为已注册用户的邮箱。重新登录后，管理员入口会在前端显示。

### 3. 前端运行

使用 HBuilderX 打开 `frontend` 目录。

检查后端地址：

```js
// frontend/config.js
export const API_BASE_URL = 'http://127.0.0.1:8000'
```

然后选择运行到浏览器、手机或小程序模拟器。

真机调试时，需要将 `127.0.0.1` 改为后端电脑的局域网 IP。

## 常用命令

```bash
# 后端迁移
cd backend
alembic upgrade head

# 后端启动
uvicorn main:app --reload

# 设置管理员
python create_admin.py admin@example.com
```

## 注意事项

- 不要提交 `backend/.env`。
- 不要提交真实 API Key、数据库密码、邮箱授权码。
- Redis 未启动时，起名接口会因限流保护而不可用。
- 使用知识库功能前，需要确保 Ollama 和 Embedding 模型可用。
- 导出 PDF / PNG 依赖 `reportlab` 和 `Pillow`。
- 生产环境应限制 CORS 域名，并使用强随机 `JWT_SECRET_KEY`。

---

## English

AIName is a full-stack AI naming application built with FastAPI and Vue 3 / uni-app. It supports name generation for people, companies, and pets, with multi-turn refinement, favorites, exportable reports, private/public knowledge bases, quota control, and admin statistics.

### Features

- Email verification, registration, and login
- JWT authentication
- User profile, password, email, login history, and account cancellation
- AI name generation for people, companies, and pets
- Multi-turn feedback and regeneration
- Naming history and favorites
- Favorite export:
  - Personal / pet names: PDF or PNG
  - Company names: PDF naming report with reference, meaning, domain, and domain status
- Private and public knowledge-base management
- Admin user management
- DeepSeek token usage statistics
- Redis-based rate limiting and quota control

### Stack

Backend: FastAPI, SQLAlchemy, Alembic, MySQL, PostgreSQL, Redis, LangChain, LangGraph, DeepSeek, Chroma, Ollama Embeddings, ReportLab, Pillow.

Frontend: Vue 3, uni-app, Composition API, and `uni.request`.

### Quick Start

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

Open `frontend` with HBuilderX, configure `frontend/config.js`, and run it in a browser, mobile device, or mini-program environment.

### Security

- Never commit `.env` or real credentials.
- Use a strong `JWT_SECRET_KEY`.
- Restrict CORS origins in production.
- Keep API keys and passwords in environment variables.

## License

No license has been specified yet. All rights are reserved unless a license is added to this repository.
