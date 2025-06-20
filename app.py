from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user  # Added current_user import
from flask_migrate import Migrate
from extensions import db
from models.users import Users
from models import Studies
from routes.admin import admin_bp
from routes.review import review_bp
from routes.study import study_bp
from routes.dashboard import dashboard_bp
from routes.auth import auth_bp
from services.data_loader import load_images_from_static
import click
from werkzeug.security import generate_password_hash
from flask_wtf.csrf import CSRFProtect

def register_commands(app):
    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("password")
    def create_admin(username, password):
        """Create an admin user"""
        if Users.query.filter_by(username=username).first():
            print("User already exists!")
            return

        admin = Users(
            username=username,
            password_hash=generate_password_hash(password),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user {username} created successfully!")

    @app.cli.command("generate-ocr")
    def generate_ocr_command():
        """Generate OCR text for all images"""
        from services.ocr_processor import generate_ocr_for_all_images
        generate_ocr_for_all_images()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Users.query.get(int(user_id))

    @app.context_processor
    def inject_common_data():
        # This will be available in all templates
        context = {
            'current_study': None  # Default value, can be overridden in routes
        }
        
        if current_user.is_authenticated:
            context['all_studies'] = Studies.query.all()
        
        return context

    # Register blueprints
    app.register_blueprint(admin_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(study_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    # Apply CSRF protection to all blueprints
    for bp in [admin_bp, review_bp, study_bp, auth_bp, dashboard_bp]:
        csrf.exempt(bp)  # Remove this line if you want CSRF on all routes

    with app.app_context():
        db.create_all()
        try:
            load_images_from_static()
        except Exception as e:
            print(f"Error loading images: {e}")
    
    register_commands(app)
            
    @app.route('/test')
    def test():
        return "Flask is running!"

    # Removed redundant /dashboard route, now handled by dashboard_bp with prefix /home

    return app
