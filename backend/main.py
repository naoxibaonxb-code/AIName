import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
from fastapi import FastAPI

from routers.auth_router import router as auth_router
from routers.name_router import router as name_router
from routers.rag_router import router as rag_router
from routers.admin_router import router as admin_router
from routers.user_router import router as user_router
from core.workflow import close_naming_workflow, initialize_naming_workflow
from core.database import engine
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()
app.include_router(auth_router)
app.include_router(name_router)
app.include_router(rag_router)
app.include_router(admin_router)
app.include_router(user_router)


@app.on_event("startup")
async def open_postgres_pool():
    await initialize_naming_workflow()


@app.on_event("shutdown")
async def close_postgres_pool():
    await close_naming_workflow()
    await engine.dispose()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议替换为具体的前端域名，如 ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法（包括 OPTIONS, POST, GET 等）
    allow_headers=["*"],  # 允许所有请求头（包括 Authorization, Content-Type 等）
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


# ====================
from fastapi import Depends
from fastapi_mail import FastMail, MessageSchema, MessageType
from dependencies import get_mail
from aiosmtplib import SMTPResponseException


@app.get("/mail/test")
async def mail_test(email: str, mail: FastMail = Depends(get_mail)):
    message = MessageSchema(
        subject="Test Subject",
        recipients=[email],
        body=f"hello {email}",
        subtype=MessageType.plain
    )
    try:
        await mail.send_message(message)
    except SMTPResponseException as e:
        if e.code == -1 and b"\\x00\\x00\\x00" in str(e).encode():
            print("忽略QQ邮箱SMTP关闭阶段的非标准相应，邮件已发送成功")
    return {"message": "邮件发送成功！"}
