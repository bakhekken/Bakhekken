import os
from pathlib import Path
from flask import Flask, render_template, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from models import db, User, Page, SiteSettings, Upload
from forms import LoginForm, PageEditForm, SettingsForm, UploadForm

BASE_DIR = Path(__file__).resolve().parent

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change_this_secret_key")
    instance_dir = BASE_DIR / "instance"
    instance_dir.mkdir(exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(instance_dir / "site.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    upload_dir = BASE_DIR / "static" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_dir)
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "admin_login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    def ensure_defaults():
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings(site_title="Dyrevenner Bak Hekken")
            db.session.add(settings)

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin")
            admin.set_password("bytt_meg_no")
            db.session.add(admin)

        def add_page(slug, title, hidden, card_enabled, card_title):
            p = Page.query.filter_by(slug=slug).first()
            if not p:
                db.session.add(Page(
                    slug=slug,
                    title=title,
                    is_hidden=hidden,
                    card_enabled=card_enabled,
                    card_title=card_title,
                    content_html=""
                ))

        add_page("om-oss", "Om oss", False, True, "Om oss")
        add_page("kontakt", "Kontakt", False, True, "Kontakt")
        add_page("adopter-kanin", "Adopter kanin", False, True, "Adopter kanin")
        add_page("side1", "Side 1", True, False, "Side 1")
        add_page("side2", "Side 2", True, False, "Side 2")

        db.session.commit()

    @app.context_processor
    def inject_globals():
        settings = SiteSettings.query.first()
        nav_pages = Page.query.filter_by(is_hidden=False).order_by(Page.id.asc()).all()
        return dict(site_settings=settings, nav_pages=nav_pages)

    @app.route("/")
    def index():
        cards = Page.query.filter_by(is_hidden=False).order_by(Page.id.asc()).all()
        cards = [p for p in cards if p.card_enabled]
        return render_template("index.html", cards=cards)

    @app.route("/p/<slug>")
    def page(slug):
        p = Page.query.filter_by(slug=slug).first_or_404()
        return render_template("page.html", page=p)

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if current_user.is_authenticated:
            return redirect(url_for("admin_dashboard"))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data.strip()).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                return redirect(url_for("admin_dashboard"))
            flash("Feil brukarnamn eller passord", "error")
        return render_template("admin_login.html", form=form)

    @app.route("/admin/logout")
    @login_required
    def admin_logout():
        logout_user()
        return redirect(url_for("index"))

    @app.route("/admin")
    @login_required
    def admin_dashboard():
        pages = Page.query.order_by(Page.id.asc()).all()
        uploads = Upload.query.order_by(Upload.uploaded_at.desc()).limit(30).all()
        upload_form = UploadForm()
        return render_template("admin_dashboard.html", pages=pages, uploads=uploads, upload_form=upload_form)

    @app.route("/admin/settings", methods=["GET", "POST"])
    @login_required
    def admin_settings():
        settings = SiteSettings.query.first()
        form = SettingsForm(obj=settings)
        if form.validate_on_submit():
            settings.site_title = form.site_title.data.strip()
            settings.primary_color = form.primary_color.data.strip()
            settings.font_family = form.font_family.data.strip()
            db.session.commit()
            flash("Innstillingar lagra", "ok")
            return redirect(url_for("admin_settings"))
        return render_template("admin_settings.html", form=form)

    @app.route("/admin/page/<int:page_id>", methods=["GET", "POST"])
    @login_required
    def admin_edit_page(page_id):
        p = db.session.get(Page, page_id)
        if not p:
            flash("Fann ikkje sida", "error")
            return redirect(url_for("admin_dashboard"))

        form = PageEditForm(obj=p)

        if form.validate_on_submit():
            p.title = form.title.data.strip()
            p.slug = form.slug.data.strip()
            p.is_hidden = bool(form.is_hidden.data)

            p.card_enabled = bool(form.card_enabled.data)
            p.card_title = (form.card_title.data or "").strip()
            p.content_html = form.content_html.data or ""

            if form.card_image.data:
                file = form.card_image.data
                safe_name = secure_filename(file.filename)
                if safe_name:
                    _, ext = os.path.splitext(safe_name)
                    final_name = f"{p.slug}{ext.lower()}"
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], final_name)
                    file.save(save_path)
                    p.card_image = final_name
                    db.session.add(Upload(filename=final_name, original_name=file.filename))

            db.session.commit()
            flash("Side lagra", "ok")
            return redirect(url_for("admin_edit_page", page_id=p.id))

        return render_template("admin_edit_page.html", form=form, page=p)

    @app.route("/admin/upload", methods=["POST"])
    @login_required
    def admin_upload():
        form = UploadForm()
        if not form.validate_on_submit():
            flash("Vel eit bilete som er jpg png webp", "error")
            return redirect(url_for("admin_dashboard"))

        file = form.file.data
        safe_name = secure_filename(file.filename)
        if not safe_name:
            flash("Ugyldig filnamn", "error")
            return redirect(url_for("admin_dashboard"))

        base, ext = os.path.splitext(safe_name)
        final_name = safe_name
        counter = 1
        while os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], final_name)):
            final_name = f"{base}_{counter}{ext}"
            counter += 1

        file.save(os.path.join(app.config["UPLOAD_FOLDER"], final_name))
        db.session.add(Upload(filename=final_name, original_name=file.filename))
        db.session.commit()
        flash("Bilete lasta opp", "ok")
        return redirect(url_for("admin_dashboard"))

    with app.app_context():
        db.create_all()
        ensure_defaults()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
