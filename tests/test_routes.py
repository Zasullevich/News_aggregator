from news_app.extensions import db_session
from news_app.models import NewsItem, Source, User
from news_app.services.parsing import SourceType


def register(client, email="user@example.com", password="password123"):
    return client.post(
        "/register",
        data={"email": email, "password": password, "password_confirm": password},
        follow_redirects=True,
    )


def test_register_login_logout(client):
    response = register(client)
    assert "Лента".encode("utf-8") in response.data

    response = client.post("/logout", follow_redirects=True)
    assert "Вход".encode("utf-8") in response.data

    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "password123"},
        follow_redirects=True,
    )
    assert "Лента".encode("utf-8") in response.data


def test_register_rejects_password_mismatch(client):
    response = client.post(
        "/register",
        data={
            "email": "mismatch@example.com",
            "password": "password123",
            "password_confirm": "password456",
        },
        follow_redirects=True,
    )

    assert "Пароли не совпадают.".encode("utf-8") in response.data
    assert User.get_by_email("mismatch@example.com") is None


def test_add_sources_detects_types(client):
    register(client)
    client.post("/sources", data={"url": "https://example.com/feed.xml"}, follow_redirects=True)
    client.post("/sources", data={"url": "https://t.me/s/example"}, follow_redirects=True)

    sources = db_session.query(Source).order_by(Source.id).all()
    assert [source.source_type for source in sources] == [SourceType.RSS, SourceType.TELEGRAM]


def test_user_sees_only_own_news(client):
    register(client, "one@example.com")
    user_one = User.get_by_email("one@example.com")
    source_one = Source(user_id=user_one.id, url="https://example.com/1.xml", source_type=SourceType.RSS, title="One")
    db_session.add(source_one)
    db_session.flush()
    db_session.add(
        NewsItem(
            user_id=user_one.id,
            source_id=source_one.id,
            external_id="one",
            title="Visible",
            text="Visible text",
            original_url="https://example.com/visible",
        )
    )
    user_two = User(email="two@example.com")
    user_two.set_password("password123")
    source_two = Source(user=user_two, url="https://example.com/2.xml", source_type=SourceType.RSS, title="Two")
    db_session.add_all([user_two, source_two])
    db_session.flush()
    db_session.add(
        NewsItem(
            user_id=user_two.id,
            source_id=source_two.id,
            external_id="two",
            title="Hidden",
            text="Hidden text",
            original_url="https://example.com/hidden",
        )
    )
    db_session.commit()

    response = client.get("/")
    assert b"Visible" in response.data
    assert b"Hidden" not in response.data


def test_cannot_delete_other_users_source(client):
    register(client, "owner@example.com")
    other = User(email="other@example.com")
    other.set_password("password123")
    source = Source(user=other, url="https://example.com/private.xml", source_type=SourceType.RSS, title="Private")
    db_session.add_all([other, source])
    db_session.commit()

    response = client.post(f"/sources/{source.id}/delete")

    assert response.status_code == 404
    assert db_session.get(Source, source.id) is not None


def test_delete_own_source(client):
    register(client)
    client.post("/sources", data={"url": "https://example.com/feed.xml"}, follow_redirects=True)
    source = db_session.query(Source).one()

    response = client.post(f"/sources/{source.id}/delete", follow_redirects=True)

    assert "Источник удален.".encode("utf-8") in response.data
    assert db_session.get(Source, source.id) is None
