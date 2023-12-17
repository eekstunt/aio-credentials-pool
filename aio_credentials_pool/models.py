from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Credential(Base):
    __tablename__ = 'credentials'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, unique=True, nullable=False, index=True)
    password = Column(Text, nullable=False)
    cookie = Column(Text, nullable=True)
    in_use = Column(Boolean, default=False, nullable=False)
    date_last_usage = Column(DateTime, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
