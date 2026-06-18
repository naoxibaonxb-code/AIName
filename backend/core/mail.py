# core/mail.py
from fastapi_mail import FastMail, ConnectionConfig
from settings.config import settings

def create_mail_instance() -> FastMail:
    mail_config = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
    return FastMail(mail_config)

# 也可以在这里直接创建一个全局单例，方便直接导入使用
mail_client = create_mail_instance()