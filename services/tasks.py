from services.data_loader import sync_images_from_remote_server
from services.ocr_image_extractor import ocr_processor
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
        logger.info("Connecting to remote server and listing files...")
        new_images_count, new_studies_count, errors = sync_images_from_remote_server(study_id=study_id)
        
        # Log all errors and warnings
        if errors:
            for error in errors:
                if "Limited sync to" in error or "DRY_RUN" in error:
                    logger.warning(error)
                else:
                    logger.error(error)
        
        if new_images_count > 0 or new_studies_count > 0:
            logger.info(f"Sync completed successfully: {new_images_count} new images, {new_studies_count} new studies added.")
        else:
            logger.info("Sync completed: No new images or studies to add.")
            
        return new_images_count, new_studies_count, errors
    except Exception as e:
        logger.error(f"Error during sync task: {str(e)}")
        logger.error(f"Sync task failed for study_id: {study_id}")
        raise

@celery.task(name='process_ocr_task')
def process_ocr_task(study_id=None, image_ids=None, limit_per_study=0):
    """
    Celery task to process OCR for images in the background.
    Can process all images, images for a specific study, or specific image IDs.
    Logs progress and errors for visibility.
    """
    image_count = len(image_ids) if image_ids else 'All'
    logger.info(f"Starting OCR processing task for {study_id if study_id else 'All Studies'} with {image_count} images")
    try:
        if study_id:
            processed_count = ocr_processor.process_images_for_study(study_id)
        elif image_ids:
            processed_count = ocr_processor.process_images(specific_ids=image_ids)
        else:
            processed_count = ocr_processor.process_images(limit_per_study=limit_per_study)
        logger.info(f"OCR processing completed: {processed_count} images processed.")
        return processed_count
    except Exception as e:
        logger.error(f"Error during OCR processing task: {str(e)}")
        raise
