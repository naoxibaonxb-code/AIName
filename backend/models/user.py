# models/user.py
from datetime import datetime

from pwdlib import PasswordHash
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base

password_hash = PasswordHash.recommended()


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    username: Mapped[str] = mapped_column(String(100))
    _password: Mapped[str] = mapped_column(String(200))

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
