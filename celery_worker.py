from app import create_app
from celery import Celery
from services.ocr_service import OCRService

def make_celery(app):
    celery = Celery(
        app.import_name,
        # backend=app.config['CELERY_RESULT_BACKEND'],
        # broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

app = create_app()
celery = make_celery(app)

@celery.task
def process_image_task(image_id):
    return OCRService.process_image(image_id)
