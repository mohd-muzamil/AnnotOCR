from app import create_app
from celery import Celery
import os
from services.ocr_image_extractor import ocr_processor

# Create the Flask app instance
flask_app = create_app()

def make_celery(app):
    # Pull Celery config from Flask config or .env
    broker = app.config.get('CELERY_BROKER_URL') or os.getenv('CELERY_BROKER_URL')
    backend = app.config.get('result_backend') or os.getenv('CELERY_RESULT_BACKEND')

    if not broker or not backend:
        raise RuntimeError(
            "Missing Celery configuration: "
            "Set CELERY_BROKER_URL and CELERY_RESULT_BACKEND in your .env or config.py"
        )

    celery = Celery(
        app.import_name,
        broker=broker,
        backend=backend
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# Initialize Celery
celery = make_celery(flask_app)

# Ensure Celery can discover tasks in the services directory
celery.autodiscover_tasks(['services'])

# Example task
@celery.task(name="tasks.process_image_task")
def process_image_task(image_id):
    """
    Background task to process OCR for a single image.
    """
    return ocr_processor.extract_ocr_for_images([image_id])
