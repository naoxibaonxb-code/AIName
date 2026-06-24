from pathlib import Path
from uuid import uuid4

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.knowledge import KnowledgeFile
from models.user import User
from schemas.knowledge import KnowledgeFileOut, KnowledgeFileUpdateIn, KnowledgeStatsOut
from services.knowledge_queue import publish_knowledge_task

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
auth_handler = AuthHandler()

UPLOAD_DIR = Path("uploads")
ALLOWED_SUFFIXES = {".pdf", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.get("/files", response_model=list[KnowledgeFileOut])
async def list_files(
        scope: Annotated[Literal["private", "public", "all"], Query()] = "private",
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    filters = []
    if scope == "private":
        filters = [KnowledgeFile.scope == "private", KnowledgeFile.user_id == user.id]
    elif scope == "public":
        filters = [KnowledgeFile.scope == "public"]
    else:
        filters = [
            (KnowledgeFile.scope == "public")
            | ((KnowledgeFile.scope == "private") & (KnowledgeFile.user_id == user.id))
        ]
    result = await session.scalars(
        select(KnowledgeFile)
        .where(*filters)
        .order_by(KnowledgeFile.uploaded_at.desc())
    )
    return list(result)


@router.get("/stats", response_model=KnowledgeStatsOut)
async def knowledge_stats(
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    files = await session.scalars(
        select(KnowledgeFile).where(
            (KnowledgeFile.scope == "public")
            | ((KnowledgeFile.scope == "private") & (KnowledgeFile.user_id == user.id))
        )
    )
    private_total = private_ready = public_total = public_ready = 0
    for item in files:
        if item.scope == "public":
            public_total += 1
            public_ready += int(item.status == "ready" and item.is_enabled)
        else:
            private_total += 1
            private_ready += int(item.status == "ready" and item.is_enabled)
    return KnowledgeStatsOut(
        private_total=private_total,
        private_ready=private_ready,
        public_total=public_total,
        public_ready=public_ready,
    )


@router.post("/upload", response_model=KnowledgeFileOut, status_code=202)
async def upload_file(
        scope: Annotated[Literal["private", "public"], Query()] = "private",
        file: UploadFile = File(...),
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    if scope == "public" and user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以上传平台公共知识库")

    original_name = Path(file.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if not original_name or suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 PDF 和 TXT 文件")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{scope}_{user.id}_{uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / stored_name
    size = 0

    try:
        with file_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="文件不能超过 10MB")
                target.write(chunk)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    record = KnowledgeFile(
        user_id=user.id,
        original_name=original_name,
        stored_name=stored_name,
        scope=scope,
        status="pending",
        file_size=size,
        is_enabled=True,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    try:
        await publish_knowledge_task(
            action="index",
            record_id=record.id,
            file_path=str(file_path),
            user_id=user.id,
            scope=scope,
        )
    except Exception as exc:
        record.status = "failed"
        record.error_message = "知识库任务发送失败，请稍后重试"
        await session.commit()
        raise HTTPException(status_code=503, detail=record.error_message) from exc
    return record


def _ensure_file_permission(record: KnowledgeFile, user: User) -> None:
    if user.role == "admin":
        return
    if record.scope != "private" or record.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权管理此知识库文件")


@router.patch("/files/{file_id}", response_model=KnowledgeFileOut)
async def update_file(
        file_id: int,
        data: KnowledgeFileUpdateIn,
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    record = await session.get(KnowledgeFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="知识库文件不存在")
    _ensure_file_permission(record, user)

    if record.is_enabled == data.is_enabled:
        return record

    record.is_enabled = data.is_enabled
    file_path = UPLOAD_DIR / record.stored_name
    try:
        if not data.is_enabled:
            await publish_knowledge_task(
                action="delete",
                record_id=record.id,
                user_id=record.user_id,
                scope=record.scope,
            )
        elif record.status == "ready" and file_path.exists():
            record.status = "pending"
            await publish_knowledge_task(
                action="index",
                record_id=record.id,
                file_path=str(file_path),
                user_id=record.user_id,
                scope=record.scope,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="知识库任务发送失败，请稍后重试"
        ) from exc

    await session.commit()
    await session.refresh(record)
    return record


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
        file_id: int,
        user: User = Depends(auth_handler.current_user_dependency),
        session: AsyncSession = Depends(get_session)):
    record = await session.get(KnowledgeFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="知识库文件不存在")
    _ensure_file_permission(record, user)

    file_path = UPLOAD_DIR / record.stored_name
    try:
        await publish_knowledge_task(
            action="delete",
            record_id=record.id,
            user_id=record.user_id,
            scope=record.scope,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="知识库任务发送失败，请稍后重试"
        ) from exc
    await session.delete(record)
    await session.commit()
    file_path.unlink(missing_ok=True)
    return None
