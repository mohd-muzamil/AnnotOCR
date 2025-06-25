import os

class Config:
    APPLICATION_ROOT = '/annotation'

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'devkey-warning-please-set-secret-key-in-env-for-production'
    SQLALCHEMY_DATABASE_URI = "sqlite:///db/local_database.db" if os.environ.get('FLASK_ENV') == 'development' else \
        "sqlite:///db/production_database.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'warning-please-set-csrf-secret-key-in-env-for-production'  # Different from SECRET_KEY
