import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'devkey-warning-please-set-secret-key-in-env-for-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        "sqlite:////app/db/db.sqlite3"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'warning-please-set-csrf-secret-key-in-env-for-production'  # Different from SECRET_KEY
