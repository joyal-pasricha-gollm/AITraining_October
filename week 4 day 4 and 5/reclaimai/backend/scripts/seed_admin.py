from sqlalchemy import func,select
from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.enums import UserRole
from app.models.user import User
def seed():
    email=settings.admin_email.strip().lower()
    with SessionLocal() as db:
        user=db.scalar(select(User).where(func.lower(User.email)==email))
        if user:
            user.role=UserRole.ADMIN;user.is_active=True;db.commit();print("Administrator account already exists or was promoted.");return
        db.add(User(full_name=settings.admin_name,email=email,password_hash=hash_password(settings.admin_password),role=UserRole.ADMIN,is_active=True));db.commit();print("Administrator account created.")
if __name__=="__main__":seed()
