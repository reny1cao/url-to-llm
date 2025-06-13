"""Database base configuration.

This module provides the SQLAlchemy declarative base and common mixins
for all database models.
"""

from sqlalchemy import Column, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Create the declarative base
Base = declarative_base()


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps to models."""
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
        doc="Timestamp when the record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
        doc="Timestamp when the record was last updated"
    )