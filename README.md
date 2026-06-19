# AIName / 知名

AIName 是一个由大语言模型驱动的智能起名应用，可根据用户的个性化要求生成人名、企业名和宠物名。系统会为候选名字提供文化出处、寓意说明，并支持针对生成结果进行连续调整。

AIName is an AI-powered naming application that creates personalized names for people, companies, and pets. Each suggestion includes its cultural reference and meaning, and users can refine the generated results through follow-up feedback.

## 中文介绍

### 主要功能

- 邮箱验证码注册与账号登录
- JWT 登录状态认证
- 用户中心、资料与密码修改
- 登录记录、起名使用次数统计与账号注销
- 生成人名、企业名和宠物名
- 支持姓氏、性别、字数、偏好和避用字等条件
- 展示名字的文化出处与寓意
- 为企业名生成并查询 `.com` 域名状态
- 基于会话记录对结果进行多轮调整
- 上传资料并通过私有知识库辅助企业命名
- 兼容 H5、移动端和小程序的 uni-app 前端

### 技术栈

**后端**

- FastAPI
- SQLAlchemy、Alembic、MySQL
- Redis
- LangChain、LangGraph、DeepSeek
- Chroma、Ollama Embeddings
- JWT、FastAPI Mail

**前端**

- Vue 3
- uni-app
- Composition API
- uni.request

### 项目结构

```text
AIName/
├── backend/             # FastAPI 后端服务
│   ├── core/            # 认证、工作流、模型及 RAG 服务
│   ├── models/          # 数据库模型
│   ├── repository/      # 数据访问层
│   ├── routers/         # API 路由
│   ├── schemas/         # 请求与响应模型
│   ├── settings/        # 配置管理
│   ├── alembic/         # 数据库迁移
│   └── main.py          # 后端入口
├── frontend/            # Vue 3 / uni-app 前端
│   ├── pages/           # 登录、注册与起名页面
│   ├── utils/           # API 请求封装
│   ├── styles/          # 公共样式
│   └── config.js        # 后端服务地址
├── .gitignore
└── README.md
```

### 本地运行

#### 1. 后端

准备 Python、MySQL 和 Redis，并在 `backend/.env` 中配置以下服务：

- MySQL 数据库连接
- Redis 连接
- 邮箱 SMTP 服务
- JWT 密钥
- DeepSeek API Key
- PostgreSQL、Ollama 和 Chroma（使用知识库功能时需要）

进入后端目录，安装依赖并启动服务：

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

默认接口地址为 `http://127.0.0.1:8000`，接口文档位于 `http://127.0.0.1:8000/docs`。

#### 创建管理员

管理员不能通过公开注册接口创建。先注册一个普通用户，执行数据库迁移后，在 `backend` 目录运行：

```bash
python create_admin.py admin@example.com
```

将示例邮箱替换为已注册账号的邮箱。重新登录后，首页会显示“用户管理”入口，可查看、搜索、禁用或恢复普通用户。

#### 2. 前端

1. 使用 HBuilderX 打开 `frontend` 目录。
2. 检查 `frontend/config.js` 中的 `API_BASE_URL`。
3. 选择运行到浏览器、手机或对应小程序。

浏览器本地调试可使用 `http://127.0.0.1:8000`；真机调试时需改为后端电脑的局域网 IP 地址。

### 安全说明

- 不要将 `backend/.env` 提交到 GitHub。
- 生产环境应使用高强度且唯一的 `JWT_SECRET_KEY`。
- 正式部署时应限制后端 CORS 允许的域名。
- API Key、数据库密码和邮箱授权码应通过环境变量管理。

---

## English

### Features

- Email verification, registration, and login
- JWT-based authentication
- User profile and password management
- Login history, usage statistics, and account cancellation
- AI-generated names for people, companies, and pets
- Custom surname, gender, length, preferences, and excluded characters
- Cultural references and meaning explanations
- `.com` domain suggestions and availability checks for company names
- Multi-turn refinement based on user feedback
- Private knowledge-base support for company naming
- Cross-platform frontend built with Vue 3 and uni-app

### Tech Stack

**Backend:** FastAPI, SQLAlchemy, Alembic, MySQL, Redis, LangChain, LangGraph, DeepSeek, Chroma, Ollama Embeddings, JWT, and FastAPI Mail.

**Frontend:** Vue 3, uni-app, Composition API, and `uni.request`.

### Getting Started

#### Backend

Set up Python, MySQL, and Redis, then configure database, email, JWT, and DeepSeek credentials in `backend/.env`. PostgreSQL, Ollama, and Chroma are also required when using the private knowledge-base features.

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000` by default. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

#### Create an Administrator

Administrator accounts cannot be created through public registration. Register a regular user first, apply the database migration, and run the following command from `backend`:

```bash
python create_admin.py admin@example.com
```

Replace the example address with the email of an existing user. After signing in again, the administrator can view, search, disable, and restore regular users.

#### Frontend

1. Open the `frontend` directory in HBuilderX.
2. Set the backend URL in `frontend/config.js`.
3. Run the project in a browser, mobile app, or supported mini-program environment.

For testing on a physical device, replace `127.0.0.1` with the local network IP address of the computer running the backend.

### Security

- Never commit `backend/.env` or any real credentials.
- Use a strong and unique `JWT_SECRET_KEY` in production.
- Restrict allowed CORS origins before deployment.
- Keep API keys, database passwords, and email authorization codes in environment variables.

## License

No license has been specified yet. All rights are reserved unless a license is added to this repository.
