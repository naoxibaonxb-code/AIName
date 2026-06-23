from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.announcement import Announcement
from models.user import User
from schemas.announcement import AnnouncementIn, AnnouncementOut, AnnouncementPageOut, AnnouncementUpdateIn
from schemas.response import ResponseOut

router = APIRouter(tags=["announcement"])
auth_handler = AuthHandler()


def active_filters(now: datetime):
    return [
        Announcement.is_active.is_(True),
        ((Announcement.starts_at.is_(None)) | (Announcement.starts_at <= now)),
        ((Announcement.expires_at.is_(None)) | (Announcement.expires_at >= now)),
    ]


@router.get("/announcements/active", response_model=list[AnnouncementOut])
async def active_announcements(
        session: AsyncSession = Depends(get_session)):
    now = datetime.now()
    result = await session.scalars(
        select(Announcement)
        .where(*active_filters(now))
        .order_by(Announcement.created_at.desc())
        .limit(3)
    )
    return list(result)


@router.get("/admin/announcements", response_model=AnnouncementPageOut)
async def admin_list_announcements(
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        _: User = Depends(auth_handler.admin_dependency),
        session: AsyncSession = Depends(get_session)):
    total = await session.scalar(select(func.count(Announcement.id)))
    result = await session.scalars(
        select(Announcement)
        .order_by(Announcement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AnnouncementPageOut(
        items=list(result), total=total or 0, page=page, page_size=page_size
    )


@router.post("/admin/announcements", response_model=AnnouncementOut, status_code=201)
async def admin_create_announcement(
        data: AnnouncementIn,
        _: User = Depends(auth_handler.admin_dependency),
        session: AsyncSession = Depends(get_session)):
    if data.starts_at and data.expires_at and data.starts_at >= data.expires_at:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    item = Announcement(**data.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.patch("/admin/announcements/{announcement_id}", response_model=AnnouncementOut)
async def admin_update_announcement(
        announcement_id: int,
        data: AnnouncementUpdateIn,
        _: User = Depends(auth_handler.admin_dependency),
        session: AsyncSession = Depends(get_session)):
    item = await session.get(Announcement, announcement_id)
    if not item:
        raise HTTPException(status_code=404, detail="公告不存在")
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(item, key, value)
    if item.starts_at and item.expires_at and item.starts_at >= item.expires_at:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    item.updated_at = datetime.now()
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/admin/announcements/{announcement_id}", response_model=ResponseOut)
async def admin_delete_announcement(
        announcement_id: int,
        _: User = Depends(auth_handler.admin_dependency),
        session: AsyncSession = Depends(get_session)):
    item = await session.get(Announcement, announcement_id)
    if not item:
        raise HTTPException(status_code=404, detail="公告不存在")
    await session.delete(item)
    await session.commit()
    return ResponseOut(message="公告已删除")
