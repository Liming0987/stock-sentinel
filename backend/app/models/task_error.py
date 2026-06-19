from sqlalchemy import Column, Integer, String, Text, DateTime, text
from app.models.database import Base


class TaskError(Base):
    __tablename__ = "task_errors"

    id = Column(Integer, primary_key=True)
    task_name = Column(String(100), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        index=True,
    )
