import asyncio

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from news_app.extensions import db_session
from news_app.models import NewsItem, Source, User
from news_app.services.parsing import detect_source_type
from news_app.services.refresh import refresh_source


bp = Blueprint("main", __name__)


@bp.get("/")
@login_required
def index():
    source_id = request.args.get("source_id", type=int)
    query = (
        db_session.query(NewsItem)
        .join(Source)
        .filter(NewsItem.user_id == current_user.id)
        .order_by(NewsItem.published_at.desc().nullslast(), NewsItem.collected_at.desc())
    )
    if source_id:
        query = query.filter(NewsItem.source_id == source_id)
    items = query.limit(100).all()
    sources = (
        db_session.query(Source)
        .filter(Source.user_id == current_user.id)
        .order_by(Source.created_at.desc())
        .all()
    )
    return render_template("index.html", items=items, sources=sources, selected_source_id=source_id)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        if not email or len(password) < 8:
            flash("Введите email и пароль не короче 8 символов.", "error")
            return render_template("register.html")
        if password != password_confirm:
            flash("Пароли не совпадают.", "error")
            return render_template("register.html")
        user = User(email=email)
        user.set_password(password)
        db_session.add(user)
        try:
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
            flash("Пользователь с таким email уже существует.", "error")
            return render_template("register.html")
        login_user(user)
        return redirect(url_for("main.index"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        user = User.get_by_email(email)
        if not user or not user.check_password(password):
            flash("Неверный email или пароль.", "error")
            return render_template("login.html")
        login_user(user)
        return redirect(url_for("main.index"))
    return render_template("login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@bp.route("/sources", methods=["GET"])
@login_required
def sources():
    user_sources = (
        db_session.query(Source)
        .filter(Source.user_id == current_user.id)
        .order_by(Source.created_at.desc())
        .all()
    )
    return render_template("sources.html", sources=user_sources)


@bp.post("/sources")
@login_required
def add_source():
    url = request.form.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        flash("Добавьте полную ссылку, начиная с http:// или https://.", "error")
        return redirect(url_for("main.sources"))

    source_type = detect_source_type(url)
    source = Source(
        user_id=current_user.id,
        url=url,
        source_type=source_type,
        title=url,
    )
    db_session.add(source)
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
        flash("Этот источник уже добавлен.", "error")
        return redirect(url_for("main.sources"))

    flash("Источник добавлен. Первое обновление можно запустить вручную.", "success")
    return redirect(url_for("main.sources"))


@bp.post("/sources/<int:source_id>/delete")
@login_required
def delete_source(source_id):
    source = _current_user_source(source_id)
    db_session.delete(source)
    db_session.commit()
    flash("Источник удален.", "success")
    return redirect(url_for("main.sources"))


@bp.post("/sources/<int:source_id>/refresh")
@login_required
def refresh_source_route(source_id):
    source = _current_user_source(source_id)
    result = asyncio.run(refresh_source(source.id))
    if result.error:
        flash(f"Не удалось обновить источник: {result.error}", "error")
    else:
        flash(f"Источник обновлен, добавлено новостей: {result.saved_count}.", "success")
    return redirect(url_for("main.sources"))


def _current_user_source(source_id):
    source = (
        db_session.query(Source)
        .filter(Source.id == source_id, Source.user_id == current_user.id)
        .one_or_none()
    )
    if source is None:
        abort(404)
    return source
