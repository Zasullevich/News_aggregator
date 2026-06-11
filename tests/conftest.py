import pytest

from news_app import create_app
from news_app import extensions
from news_app.extensions import db_session
from news_app.models import Base


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test",
            "DATABASE_URL": "sqlite:///" + str(tmp_path / "test.sqlite"),
            "DISABLE_SCHEDULER": True,
        }
    )
    yield app
    db_session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_database(app):
    yield
    Base.metadata.drop_all(bind=extensions.engine)
