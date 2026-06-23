from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from dependencies import get_session
from models.user import User
from settings.config import settings


class AuthHandler:
    security = HTTPBearer()
    access_token_type = "1"

    def encode_login_token(self, user_id: int) -> dict[str, str]:
        payload = {
            "iss": str(user_id),
            "sub": self.access_token_type,
            "exp": datetime.now(timezone.utc) + settings.JWT_ACCESS_TOKEN_EXPIRES,
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        return {"access_token": token}

    def decode_access_token(self, token: str) -> str:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=["HS256"]
            )
            if payload.get("sub") != self.access_token_type:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Token类型错误"
                )
            return payload["iss"]
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Access Token已过期"
            ) from exc
        except (jwt.InvalidTokenError, KeyError) as exc:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Token非法或已损坏"
            ) from exc

    async def _get_current_user(
            self,
            auth: HTTPAuthorizationCredentials,
            session: AsyncSession) -> User:
        user_id = int(self.decode_access_token(auth.credentials))
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="用户不存在"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="账号已被禁用"
            )
        return user

    async def auth_access_dependency(
            self,
            auth: HTTPAuthorizationCredentials = Security(security),
            session: AsyncSession = Depends(get_session)) -> int:
        user = await self._get_current_user(auth, session)
        return user.id

    async def current_user_dependency(
            self,
            auth: HTTPAuthorizationCredentials = Security(security),
            session: AsyncSession = Depends(get_session)) -> User:
        return await self._get_current_user(auth, session)

    async def admin_dependency(
            self,
            auth: HTTPAuthorizationCredentials = Security(security),
            session: AsyncSession = Depends(get_session)) -> User:
        user = await self._get_current_user(auth, session)
        if user.role != "admin":
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="需要管理员权限"
            )
        return user
