from flask_login import LoginManager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


login_manager = LoginManager()
engine = None
db_session = scoped_session(sessionmaker())

def init_database(database_url):
    global engine
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, future=True, connect_args=connect_args)
    db_session.configure(bind=engine)

def create_schema():
    from news_app.models import Base

    Base.metadata.create_all(bind=engine)

def remove_session():
    db_session.remove()
