from flask_login import UserMixin
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from news_app.extensions import db_session
from news_app.time import utc_now


Base = declarative_base()


class User(UserMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    sources = relationship("Source", back_populates="user", cascade="all, delete-orphan")
    news_items = relationship("NewsItem", back_populates="user", cascade="all, delete-orphan")

    @classmethod
    def get_by_id(cls, user_id):
        if not str(user_id).isdigit():
            return None
        return db_session.get(cls, int(user_id))

    @classmethod
    def get_by_email(cls, email):
        return db_session.query(cls).filter(cls.email == email.lower().strip()).one_or_none()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    source_type = Column(String(32), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    last_checked_at = Column(DateTime)

    user = relationship("User", back_populates="sources")
    news_items = relationship("NewsItem", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_sources_user_url"),)


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    external_id = Column(String(128), nullable=False)
    title = Column(String(500), nullable=False)
    text = Column(Text, nullable=False)
    original_url = Column(Text, nullable=False)
    published_at = Column(DateTime)
    collected_at = Column(DateTime, nullable=False, default=utc_now)

    user = relationship("User", back_populates="news_items")
    source = relationship("Source", back_populates="news_items")

    __table_args__ = (
        UniqueConstraint("user_id", "source_id", "external_id", name="uq_news_item_external_id"),
    )
