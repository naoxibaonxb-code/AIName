# models/user.py
from datetime import datetime

from pwdlib import PasswordHash
from sqlalchemy import Boolean, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base

password_hash = PasswordHash.recommended()


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    username: Mapped[str] = mapped_column(String(100))
    _password: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now()
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __init__(self, *args, **kwargs):
        password = kwargs.get("password", None)
        super().__init__(*args, **kwargs)
        if password:
            self.password = password

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = password_hash.hash(password)

    def check_password(self, password):
        return password_hash.verify(password, self.password)


class EmailCode(Base):
    __tablename__ = "email_code"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    code: Mapped[str] = mapped_column(String(100))
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class LoginRecord(Base):
    __tablename__ = "login_record"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    login_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now()
    )
    ip_address: Mapped[str] = mapped_column(String(45), default="")
    user_agent: Mapped[str] = mapped_column(String(500), default="")
