from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.models.database import Base


class AppSetting(Base):
    """Key-value store for user-configurable application settings."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
