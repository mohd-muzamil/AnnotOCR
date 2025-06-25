from services.data_loader import sync_images_from_remote_server
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Attempt to use the Celery app from celery_worker.py
try:
    from celery_worker import celery
except ImportError:
    from celery import Celery
    # Fallback to standalone Celery initialization if import fails
    celery = Celery('tasks', broker='redis://localhost:6379/0')
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )

@celery.task(name='sync_images_task')
def sync_images_task(study_id=None):
    """
    Celery task to sync images from a remote server in the background.
    Logs progress and errors for visibility.
    """
    logger.info(f"Starting image sync task for study_id: {study_id if study_id else 'All Studies'}")
    try:
        new_images_count, new_studies_count, errors = sync_images_from_remote_server(study_id=study_id)
        if errors:
            for error in errors:
                logger.error(error)
        logger.info(f"Sync completed: {new_images_count} new images, {new_studies_count} new studies added.")
        return new_images_count, new_studies_count, errors
    except Exception as e:
        logger.error(f"Error during sync task: {str(e)}")
        raise
