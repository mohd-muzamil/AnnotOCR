import os
from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash
import click
from datetime import timedelta

from extensions import db
from models.users import Users
from models import Studies
from routes.admin import admin_bp
from routes.review import review_bp
from routes.study import study_bp
from routes.dashboard import dashboard_bp
from routes.auth import auth_bp
from services.data_loader import load_images_from_static


def register_commands(app):
    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("password")
    def create_admin(username, password):
        """Create an admin user"""
        if Users.query.filter_by(username=username).first():
            # Removed print statement for user already exists
            return

        admin = Users(
            username=username,
            password_hash=generate_password_hash(password),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        # Removed print statement for admin user creation

    @app.cli.command("reset-admin-password")
    @click.argument("username")
    @click.argument("new_password")
    def reset_admin_password(username, new_password):
        """Reset an admin user's password"""
        user = Users.query.filter_by(username=username).first()
        if not user:
            # Removed print statement for user not found
            return
        
        if user.role != "admin":
            # Removed print statement for user not admin
            return
            
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        # Removed print statement for password reset

    @app.cli.command("generate-ocr")
    def generate_ocr_command():
        """Generate OCR text for all images"""
        from services.ocr_image_extractor import ocr_processor
        ocr_processor.process_images()


def create_app():
    from dotenv import load_dotenv
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Enable debug only in development
    flask_env = os.environ.get('FLASK_ENV')
    app.config['DEBUG'] = flask_env == 'development'
    # Removed print statement for FLASK_ENV and Debug

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    csrf = CSRFProtect(app)

    # Login manager setup
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    # Configure session cookie for all paths under /annotation
    app.config['SESSION_COOKIE_PATH'] = '/annotation'
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

    @login_manager.user_loader
    def load_user(user_id):
        return Users.query.get(int(user_id))

    @app.context_processor
    def inject_common_data():
        context = {'current_study': None}
        if current_user.is_authenticated:
            context['all_studies'] = Studies.query.all()
        return context

    # Register blueprints
    for bp in [admin_bp, review_bp, study_bp, auth_bp, dashboard_bp]:
        app.register_blueprint(bp)
        csrf.exempt(bp)  # Optional: remove this line to enforce CSRF

    # Initialize DB if needed
    with app.app_context():
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            # Removed print statement for creating DB
            db.create_all()
        else:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if not inspector.get_table_names():
                # Removed print statement for no tables found
                db.create_all()
            else:
                # Removed print statement for found tables
                app.logger.info("Database already initialized with tables.")

        try:
            load_images_from_static()
        except Exception as e:
            app.logger.error(f"Error loading images from static: {str(e)}")


        # Admin setup from env
        admin_username = os.getenv('ADMIN_USERNAME')
        admin_password = os.getenv('ADMIN_PASSWORD')
        if admin_username and admin_password:
            existing_admin = Users.query.filter_by(username=admin_username).first()
            if not existing_admin:
                try:
                    new_admin = Users(
                        username=admin_username,
                        password_hash=generate_password_hash(admin_password),
                        role="admin"
                    )
                    db.session.add(new_admin)
                    db.session.commit()
                    app.logger.info("Admin user created successfully from environment variables.")
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Error creating admin user: {str(e)}")
        else:
            # Removed print statement for admin env warning
            if Users.query.filter_by(role="admin").count() == 0:
                default_admin = Users(
                    username="admin",
                    password_hash=generate_password_hash("defaultpassword"),
                    role="admin"
                )
                db.session.add(default_admin)
                db.session.commit()
                # Removed print statement for default admin creation

    # Register CLI commands
    register_commands(app)

    # Redirect root of /annotation to login page
    @app.route('/')
    def root_redirect():
        return redirect(url_for('auth.login'))

    # Health check
    @app.route('/health')
    def health():
        return "Healthy", 200


    return app


# Mount app under /annotation for Nginx reverse proxy
flask_app = create_app()

# Fallback app for requests not under /annotation to prevent NoneType error
def fallback_app(environ, start_response):
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'404 Not Found']

application = DispatcherMiddleware(fallback_app, {
    '/annotation': flask_app
})

# Ensure URLs are generated with the /annotation prefix only once
@flask_app.context_processor
def override_url_for():
    def prefixed_url_for(endpoint, **values):
        url = flask_app.url_for(endpoint, **values)
        # Remove any existing /annotation prefixes to start fresh
        url = url.replace('/annotation', '')
        # Add a single /annotation prefix
        url = f"/annotation{url}"
        # Removed print statement for generated URL
        return url
    return dict(url_for=prefixed_url_for)
