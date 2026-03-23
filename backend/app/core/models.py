from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.hybrid import hybrid_property


class TimestampMixin:
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )


class SoftDeleteMixin:
    deleted_at = Column(DateTime, nullable=True)

    @hybrid_property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @is_deleted.expression
    def is_deleted(cls):
        return cls.deleted_at.isnot(None)
