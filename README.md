# AIName / 知名

AIName 是一个前后端分离、同仓库管理的 AI 起名系统。当前稳定版支持邮箱注册登录、人名 / 企业名 / 宠物名 / 虚拟 IP 起名、企业知识库 RAG、多轮反馈、历史收藏、导出、每日免费额度、支付宝沙箱购买生成机会和管理员后台。

项目当前以“基础业务可用、增强能力可降级”为原则：DeepSeek 负责起名生成，企业名可参考私有 / 公共知识库，长期记忆依赖 PostgreSQL + pgvector + Ollama Embeddings；当长期记忆不可用时，起名主流程会继续运行。

## 当前能力

- 账号体系：邮箱验证码注册、登录、JWT 鉴权、登录记录。
- 用户中心：修改用户名、修改密码、查看使用次数、注销账号；邮箱是注册账号，只读不可修改。
- AI 起名：
  - 人名 / 宝宝起名：支持姓氏、性别、长度、避用字、八字五行参考。
  - 企业 / 品牌起名：支持品牌调性、目标客群、竞品避让、RAG 知识库、`.com` 域名建议与查询。
  - 宠物名：支持性格、外貌、品种等趣味化输入。
  - 虚拟 IP：支持世界观、人设、口头禅和传播性推演。
- 多轮反馈：基于当前会话继续调整候选名。
- 历史与收藏：保存生成记录、收藏候选、删除、重新生成、导出 JSON / CSV / PDF / PNG。
- 企业知识库：用户私有知识库 + 平台公共知识库，支持 PDF / TXT 上传、启停、删除。
- RabbitMQ 异步处理：上传 / 删除知识库文件由 `rag_worker.py` 消费任务处理。
- 额度与支付：
  - 普通用户每日免费成功生成 3 次，失败不扣次数。
  - 支付宝沙箱 `0.01` 元购买 1 次生成机会。
  - 免费额度用完后自动消耗付费权益；生成失败会退回已预扣权益。
- 管理后台：用户管理、调用统计、Token 消耗、公共知识库、公告管理。
- 安全与体验：
  - 登录失败统一提示，避免账号枚举。
  - Token 非法格式不会导致 500。
  - 普通用户查看公共知识库时隐藏内部字段。
  - 默认响应增加 `Cache-Control: no-store`。
  - 前端返回导航做了兜底，减少无法返回上一页的问题。

## 技术栈

### 后端

- FastAPI
- SQLAlchemy / Alembic
- MySQL
- PostgreSQL + LangGraph checkpoint + pgvector
- Redis
- RabbitMQ
- LangChain / LangGraph
- DeepSeek
- Chroma
- Ollama Embeddings
- ReportLab / Pillow
- FastAPI Mail

### 前端

- uni-app
- Vue 3
- Composition API
- `uni.request`
- HBuilderX 运行到 H5 / App / 小程序环境

## 项目结构

```text
AIName/
├── backend/
│   ├── alembic/          # MySQL 业务表迁移
│   ├── core/             # 认证、数据库、工作流、RAG、长期记忆
│   ├── models/           # SQLAlchemy 模型
│   ├── repository/       # 数据访问层
│   ├── routers/          # FastAPI 路由
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 额度、支付、导出、清理等服务
│   ├── settings/         # 配置
│   ├── main.py           # API 入口
│   ├── rag_worker.py     # RabbitMQ 知识库消费者
│   └── requirements.txt
├── frontend/
│   ├── pages/            # uni-app 页面
│   ├── utils/            # 请求、导航工具
│   ├── config.js         # API 地址
│   └── pages.json
├── .gitignore
└── README.md
```

## 本地启动

### 1. 准备服务

需要本地或远程可用的：

- Python 3.11+
- MySQL
- PostgreSQL，并安装 `pgvector` 扩展
- Redis
- RabbitMQ
- Ollama，建议拉取 `nomic-embed-text`
- DeepSeek API Key
- 邮箱 SMTP 服务

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例文件：

```powershell
copy .env.example .env
```

Linux / macOS：

```bash
cp .env.example .env
```

核心配置项以 [backend/.env.example](backend/.env.example) 为准，常用项如下：

```env
# MySQL
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ainame

# PostgreSQL for LangGraph checkpoint and long-term memory
PG_NAME=postgresql
PG_USER=postgres
PG_PWD=your-postgres-password
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DB_NAME=ainame

# Long-term memory
MEMORY_ENABLED=True
MEMORY_EMBEDDING_MODEL=nomic-embed-text
MEMORY_EMBEDDING_DIM=768
MEMORY_TOP_K=4
MEMORY_TIMEOUT_SECONDS=3

# Redis / RabbitMQ / Auth / AI
REDIS_HOST=127.0.0.1
RABBITMQ_HOST=127.0.0.1
JWT_SECRET_KEY=replace-with-a-long-random-secret
DEEPSEEK_API_KEY=your-deepseek-api-key

# Quota
DAILY_FREE_GENERATIONS=3

# Alipay sandbox, optional
ALIPAY_SANDBOX_ENABLED=False
ALIPAY_APP_ID=your-sandbox-app-id
ALIPAY_PRIVATE_KEY=your-sandbox-app-private-key
ALIPAY_PUBLIC_KEY=your-alipay-sandbox-public-key
ALIPAY_NOTIFY_URL=http://127.0.0.1:8000/payments/alipay/notify
ALIPAY_RETURN_URL=http://127.0.0.1:8000/payments/alipay/return-page
ALIPAY_FRONTEND_RETURN_URL=http://127.0.0.1:5173/#/pages/profile/profile
```

### 4. 初始化数据库

业务表迁移：

```bash
alembic upgrade head
```

LangGraph checkpoint 表会在后端启动时通过 `checkpoint_saver.setup()` 自动初始化。

长期记忆表会在 `MEMORY_ENABLED=True` 时自动初始化；如果 PostgreSQL / pgvector / Ollama Embeddings 不可用，系统会降级为无长期记忆模式。

### 5. 启动后端

```bash
uvicorn main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

### 6. 启动知识库消费者

知识库上传、删除和状态变更依赖 RabbitMQ 异步任务：

```bash
python rag_worker.py
```

### 7. 启动前端

使用 HBuilderX 打开 `frontend` 目录。

检查 API 地址：

```js
// frontend/config.js
export const API_BASE_URL = 'http://127.0.0.1:8000'
```

然后运行到浏览器、App 或小程序模拟器。真机调试时，将 `127.0.0.1` 改为后端机器的局域网 IP。

## 管理员账号

先通过前端注册普通用户，再在 `backend` 目录执行：

```bash
python create_admin.py admin@example.com
```

重新登录后，前端会显示管理员入口。

## 支付沙箱测试

当前支付只用于实验环境，业务含义是：

```text
0.01 元 = 1 次生成机会
```

测试流程：

1. 在 `.env` 中配置支付宝沙箱参数，并设置 `ALIPAY_SANDBOX_ENABLED=True`。
2. 如果本地接收异步通知，使用 NATAPP 等工具将公网地址转发到 `127.0.0.1:8000`。
3. 将 `ALIPAY_NOTIFY_URL` 和 `ALIPAY_RETURN_URL` 配置为支付宝可访问的地址。
4. 前端进入个人中心 -> 生成机会。
5. 创建订单并完成沙箱支付。
6. 返回后刷新订单状态，支付成功会发放 1 次权益。
7. 免费额度用完后，再次生成会自动消耗付费权益。

如果异步通知失败，前端“刷新订单状态”会主动查询支付宝订单并补发权益。

## 常用检查命令

```powershell
# Python 语法检查
@'
import ast
from pathlib import Path
for p in Path("backend").rglob("*.py"):
    ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
print("python syntax ok")
'@ | python -

# Git 状态，Windows ownership 异常时可用
git -c safe.directory=D:/Develop/CodexProject/AIName -C D:\Develop\CodexProject\AIName status
```

## 运行注意

- 不要提交 `backend/.env` 或任何真实密钥。
- Redis 未启动时，起名限流和并发保护不可用，接口会返回保护服务不可用。
- RabbitMQ 未启动时，知识库上传 / 删除任务无法处理。
- 使用知识库前，需要运行 API 服务和 `rag_worker.py`。
- 使用长期记忆前，需要 PostgreSQL 安装 `pgvector`，并保证 Ollama Embedding 模型可用。
- 支付宝沙箱仅用于模拟支付权益，不接真实生产支付。
- 生产环境应限制 CORS 域名，并使用强随机 `JWT_SECRET_KEY`。

## English

AIName is a full-stack AI naming application built with FastAPI and uni-app / Vue 3. It supports AI name generation for people, companies, pets, and virtual IP characters, with knowledge-base RAG, multi-turn refinement, history, favorites, quota control, sandbox payment credits, and admin management.

Quick start:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
python rag_worker.py
```

Open `frontend` with HBuilderX, configure `frontend/config.js`, and run it in the target environment.

## License

No license has been specified yet. All rights are reserved unless a license is added to this repository.
