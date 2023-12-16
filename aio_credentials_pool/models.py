from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, unique=True, nullable=False)
    password = Column(Text, nullable=False)
    cookie = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
