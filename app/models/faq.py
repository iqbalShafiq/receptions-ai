from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class FAQ(Base):
    """Store FAQ for knowledge base"""
    __tablename__ = "faq"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(500))
    answer = Column(Text)
    category = Column(String(100), nullable=True)
