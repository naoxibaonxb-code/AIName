import asyncio
import sys
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from core.database import engine
from core.redis_client import redis_client
from core.workflow import close_naming_workflow, initialize_naming_workflow
from routers.admin_router import router as admin_router
from routers.announcement_router import router as announcement_router
from routers.auth_router import router as auth_router
from routers.name_router import router as name_router
from routers.rag_router import router as rag_router
from routers.history_router import router as history_router
from routers.user_router import router as user_router
from services.history_cleanup import history_cleanup_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_naming_workflow()
    cleanup_task = asyncio.create_task(history_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        await close_naming_workflow()
        await engine.dispose()
        await redis_client.aclose()


app = FastAPI(title="AIName API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def privacy_headers(request, call_next):
    response = await call_next(request)
    if request.url.path != "/health":
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


app.include_router(auth_router)
app.include_router(announcement_router)
app.include_router(name_router)
app.include_router(rag_router)
app.include_router(history_router)
app.include_router(admin_router)
app.include_router(user_router)


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}
