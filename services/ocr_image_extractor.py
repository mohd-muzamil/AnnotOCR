# services/ocr_image_extractor.py
# This script handles the processing of images to extract text using OCR (Optical Character Recognition).
# It includes functions to validate image paths, process image files, and generate OCR text for images in the database.
# The primary function, generate_ocr_for_all_images, processes images that lack OCR results, extracts text using Tesseract,
# calculates confidence scores, and stores the results in the database. It also provides a command-line interface for OCR generation.
# This service is critical for converting image data into usable text data for further analysis or review.

import os
import re
import logging
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
import pytesseract
from datetime import datetime
from multiprocessing import Pool, Manager, cpu_count
from extensions import db
from models import Images, OCRResults
from sqlalchemy import exists

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        self.tesseract_version = self._get_tesseract_version()
        self.batch_size = 100  # Optimal batch size for database commits
        self.num_processes = cpu_count() or 4

    @staticmethod
    def _get_tesseract_version():
        """Get and cache Tesseract version once"""
        try:
            version = pytesseract.get_tesseract_version()
            if version:
                match = re.search(r'(\d+\.\d+\.\d+)', str(version))
                return match.group(1) if match else "unknown"
            return "unknown"
        except Exception as e:
            logger.error(f"Error getting Tesseract version: {e}")
            return "unknown"

    @staticmethod
    def _validate_image_path(filepath):
        """Validate and resolve image path efficiently"""
        if not filepath or not isinstance(filepath, str):
            return None

        # Check most likely path first
        paths_to_try = [
            os.path.join('/app/static', filepath),
            os.path.join('static', filepath),
            filepath
        ]
        
        for path in paths_to_try:
            if os.path.exists(path) and os.path.isfile(path):
                return path
        return None

    @staticmethod
    def _process_image(image_path):
        """Process single image with resource handling"""
        try:
            with PILImage.open(image_path) as img:
                # Use image_to_string to preserve line breaks
                text = pytesseract.image_to_string(img, config=r'--oem 3 --psm 6')
                if not text.strip():
                    text = "No text detected"
                
                # For confidence, we still need image_to_data
                data = pytesseract.image_to_data(
                    img, 
                    config=r'--oem 3 --psm 6',
                    output_type=pytesseract.Output.DICT
                )
                confidences = [float(conf) for conf in data.get('conf', []) if isinstance(conf, (int, float)) and conf != -1]
                avg_confidence = round(sum(confidences)/len(confidences), 2) if confidences else 0.0
                
                return text, avg_confidence
        except Exception as e:
            logger.error(f"Error processing {image_path}: {e}")
            return None, None

    def _process_single_image(self, image):
        """Wrapper for single image processing"""
        try:
            if not image or not hasattr(image, 'filepath'):
                return image.id if image else None, None, "Invalid image object"

            image_path = self._validate_image_path(image.filepath)
            if not image_path:
                return image.id, None, "Image path not found"

            text, confidence = self._process_image(image_path)
            if confidence is not None:
                return image.id, text, confidence
            return image.id, None, "OCR processing failed"
        except Exception as e:
            return image.id if image else None, None, f"Unexpected error: {e}"

    def _filter_unprocessed_images(self, images):
        """Efficiently filter out already processed images"""
        processed_ids = db.session.query(OCRResults.image_id).distinct()
        return [img for img in images if img.id not in processed_ids]

    def _save_results_batch(self, results_batch):
        """Save a batch of results efficiently, updating existing records if they exist"""
        if not results_batch:
            logger.info("No results to save in batch.")
            return 0

        updated_count = 0
        new_count = 0

        for image_id, text, confidence in results_batch:
            if confidence is None:
                continue
                
            # Check if an OCR result already exists for this image
            existing_result = db.session.query(OCRResults).filter_by(image_id=image_id).first()
            if existing_result:
                # Update existing record
                existing_result.text = text
                existing_result.confidence = confidence
                existing_result.language = 'eng'
                existing_result.version = self.tesseract_version
                existing_result.created_at = datetime.utcnow()
                updated_count += 1
                logger.info(f"Updated OCR results for image ID {image_id}.")
            else:
                # Create new record
                new_result = OCRResults(
                    image_id=image_id,
                    text=text,
                    confidence=confidence,
                    language='eng',
                    version=self.tesseract_version,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_result)
                new_count += 1
                logger.info(f"Created new OCR results for image ID {image_id}.")

        try:
            db.session.commit()
            logger.info(f"Saved {new_count} new and updated {updated_count} OCR results in batch.")
            return new_count + updated_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Batch save failed: {e}")
            return 0

    def process_images(self, images=None, specific_ids=None, limit_per_study=0):
        """Main processing method with progress tracking, optionally limiting participants per study"""
        try:
            # Get images to process
            if specific_ids:
                images = Images.query.filter(Images.id.in_(specific_ids)).all()
            elif images is None:
                if limit_per_study > 0:
                    # Limit to a specific number of participants per study for testing
                    from models import Participants, Studies
                    images = []
                    studies = Studies.query.all()
                    for study in studies:
                        participants = Participants.query.filter_by(study_id=study.id).limit(limit_per_study).all()
                        for participant in participants:
                            participant_images = Images.query.filter_by(participant_id=participant.id).all()
                            images.extend(participant_images)
                    logger.info(f"Limited processing to {limit_per_study} participants per study for testing.")
                else:
                    images = Images.query.all()

            # Filter out already processed images
            images = self._filter_unprocessed_images(images)
            total_images = len(images)
            
            if not total_images:
                logger.info("No unprocessed images found")
                return []

            logger.info(f"Processing {total_images} images with {self.num_processes} workers" + (f" (limited to {limit_per_study} participants per study)" if limit_per_study > 0 else "") + (f" for specific IDs: {specific_ids}" if specific_ids else ""))

            # Process images in parallel, ensuring session context for each image
            results = []
            processed_count = 0
            image_ids = [img.id for img in images]  # Extract IDs to avoid passing full objects to pool
            try:
                with Pool(processes=self.num_processes) as pool:
                    for i, result in enumerate(pool.imap_unordered(self._process_single_image_by_id, image_ids), 1):
                        image_id, text, confidence = result
                        
                        if confidence is not None:
                            results.append((image_id, text, confidence))
                            processed_count += 1
                        
                        # Save in batches
                        if i % self.batch_size == 0:
                            saved = self._save_results_batch(results)
                            results = []
                            logger.info(f"Processed {i}/{total_images} images ({saved} saved in batch)")

                        # Log progress periodically
                        if i % 10 == 0 or i == total_images:
                            logger.info(f"Progress: {i}/{total_images} ({processed_count} successful)")
            except BrokenPipeError as e:
                logger.error(f"BrokenPipeError during processing: {e}. Attempting to continue with remaining images.")
                # Fallback to single-threaded processing for remaining images if possible
                for image_id in image_ids[len(results):]:
                    result = self._process_single_image_by_id(image_id)
                    image_id, text, confidence = result
                    if confidence is not None:
                        results.append((image_id, text, confidence))
                        processed_count += 1
                    if len(results) >= self.batch_size:
                        saved = self._save_results_batch(results)
                        results = []
                        logger.info(f"Processed additional images in fallback mode ({saved} saved in batch)")

            # Save any remaining results
            if results:
                saved = self._save_results_batch(results)
                logger.info(f"Final batch: {saved} images saved")

            logger.info(f"Processing complete. Total: {total_images}, Successful: {processed_count}")
            return processed_count

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return 0

    def _process_single_image_by_id(self, image_id):
        """Wrapper for single image processing by ID to ensure session context"""
        try:
            # Re-query the image within the session context
            image = db.session.query(Images).get(image_id)
            if not image:
                return image_id, None, "Image not found in database"

            return self._process_single_image(image)
        except Exception as e:
            return image_id, None, f"Unexpected error: {e}"

    def process_images_for_study(self, study_id):
        """
        Process images for a specific study, filtering out already processed images.
        Args:
            study_id: ID of the study to process images for
        Returns:
            Number of images successfully processed
        """
        try:
            images = Images.query.filter_by(study_id=study_id).all()
            if not images:
                logger.info(f"No images found for study ID {study_id}")
                return 0
                
            # Filter out already processed images
            images = self._filter_unprocessed_images(images)
            total_images = len(images)
            
            if not total_images:
                logger.info(f"No unprocessed images found for study ID {study_id}")
                return 0
                
            logger.info(f"Processing {total_images} images for study ID {study_id} with {self.num_processes} workers")
            
            results = []
            processed_count = 0
            image_ids = [img.id for img in images]
            
            # Use smaller batches to avoid pipe issues
            batch_size = min(20, len(image_ids))  # Reduced batch size to mitigate resource issues
            
            for i in range(0, len(image_ids), batch_size):
                batch = image_ids[i:i + batch_size]
                try:
                    with Pool(processes=min(self.num_processes, batch_size)) as pool:
                        for result in pool.imap_unordered(self._process_single_image_by_id, batch):
                            image_id, text, confidence = result
                            
                            if confidence is not None:
                                results.append((image_id, text, confidence))
                                processed_count += 1
                            
                            # Save in batches
                            if len(results) >= self.batch_size:
                                saved = self._save_results_batch(results)
                                results = []
                                logger.info(f"Processed {min(i + len(batch), total_images)}/{total_images} images ({saved} saved in batch) for study ID {study_id}")
                except BrokenPipeError as e:
                    logger.error(f"BrokenPipeError processing batch starting at {i}: {e}. Falling back to single-threaded processing for this batch.")
                    for image_id in batch:
                        result = self._process_single_image_by_id(image_id)
                        image_id, text, confidence = result
                        if confidence is not None:
                            results.append((image_id, text, confidence))
                            processed_count += 1
                        if len(results) >= self.batch_size:
                            saved = self._save_results_batch(results)
                            results = []
                            logger.info(f"Processed additional images in fallback mode ({saved} saved in batch) for study ID {study_id}")
                except Exception as e:
                    logger.error(f"Error processing batch starting at {i}: {e}")
                    continue
            
            # Save any remaining results
            if results:
                saved = self._save_results_batch(results)
                logger.info(f"Final batch for study ID {study_id}: {saved} images saved")

            logger.info(f"Processing complete for study ID {study_id}. Total: {total_images}, Successful: {processed_count}")
            return processed_count

        except Exception as e:
            logger.error(f"Processing failed for study ID {study_id}: {e}")
            return 0

    def extract_ocr_for_images(self, image_ids):
        """
        Extract OCR for specific images and return results without saving to DB
        Args:
            image_ids: List of image IDs to process
        Returns:
            List of dictionaries with image_id, text, and confidence
        """
        try:
            images = Images.query.filter(Images.id.in_(image_ids)).all()
            if not images:
                logger.warning("No images found with the provided IDs")
                return []

            results = []
            with Pool(processes=self.num_processes) as pool:
                for result in pool.imap_unordered(self._process_single_image, images):
                    image_id, text, confidence = result
                    if confidence is not None:
                        results.append({
                            'image_id': image_id,
                            'text': text,
                            'confidence': confidence,
                            'status': 'success'
                        })
                    else:
                        results.append({
                            'image_id': image_id,
                            'error': text,  # In this case, 'text' contains the error message
                            'status': 'failed'
                        })

            logger.info(f"OCR extraction complete for {len(image_ids)} images")
            return results

        except Exception as e:
            logger.error(f"Error in extract_ocr_for_images: {e}")
            return [{
                'error': str(e),
                'status': 'failed'
            } for _ in image_ids]

# Singleton instance for the application
ocr_processor = OCRProcessor()

# Removed command-line interface functions as they are not necessary for core OCR processing
