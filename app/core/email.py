import logging
import smtplib
from email.message import EmailMessage
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)

def _send_email_sync(to_email: str, otp_code: str) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(f"SMTP Credentials not set. Simulating email to {to_email} with OTP {otp_code}")
        return

    msg = EmailMessage()
    msg['Subject'] = "Mã xác thực Đặt lại Mật khẩu (OTP)"
    msg['From'] = settings.smtp_from_email or settings.smtp_user
    msg['To'] = to_email

    body = f"""
    Xin chào,

    Mã OTP xác thực đặt lại mật khẩu của bạn là: {otp_code}

    Mã này sẽ hết hạn trong 10 phút.
    Vui lòng không chia sẻ mã này cho bất kỳ ai.

    Trân trọng,
    Medical Management System
    """
    msg.set_content(body)

    try:
        # Connect to SMTP server
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            
            # Use app password sent by the user
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
            logger.info(f"OTP Email successfully sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}. Error: {e}")
        raise e

async def send_otp_email(to_email: str, otp_code: str) -> None:
    """
    Gửi email OTP trên một event loop thread phụ để tránh block FastAPI.
    """
    await asyncio.to_thread(_send_email_sync, to_email, otp_code)
