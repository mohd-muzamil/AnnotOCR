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
from extensions import db
from models import Image, OCRResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_image_path(filepath):
    """Resolve correct image path with enhanced validation"""
    if not filepath or not isinstance(filepath, str):
        logger.error(f"Invalid filepath: {filepath}")
        return None

    possible_paths = [
        os.path.join('/app/static', filepath),
        os.path.join('static', filepath),
        filepath
    ]
    
    for path in possible_paths:
        try:
            if os.path.exists(path) and os.path.isfile(path):
                return path
        except (TypeError, ValueError) as e:
            logger.error(f"Path validation error for {path}: {e}")
            continue
    
    logger.error(f"Image not found at any path: {filepath}")
    return None

def get_tesseract_simple_version():
    """Get simplified Tesseract version with validation"""
    try:
        version = pytesseract.get_tesseract_version()
        if version:
            match = re.search(r'(\d+\.\d+\.\d+)', str(version))
            return match.group(1) if match else "unknown"
        return "unknown"
    except Exception as e:
        logger.error(f"Error getting Tesseract version: {e}")
        return "unknown"

def process_image_file(image_path):
    """Safely process image file with validation"""
    if not image_path:
        return None, 0.0

    try:
        with open(image_path, 'rb') as f:
            # Verify it's an image file by reading first few bytes
            header = f.read(4)
            if not header.startswith(b'\x89PNG') and not header.startswith(b'\xff\xd8'):
                logger.error(f"Invalid image format for {image_path}")
                return None, 0.0

        img = PILImage.open(image_path)
        return img, 1.0  # Return image and dummy confidence if we get here
    except (IOError, OSError, UnidentifiedImageError) as e:
        logger.error(f"Error opening image {image_path}: {e}")
        return None, 0.0
    except Exception as e:
        logger.error(f"Unexpected error processing {image_path}: {e}")
        return None, 0.0

def generate_ocr_for_all_images():
    """Generate OCR text with enhanced error handling"""
    try:
        images_with_ocr = db.session.query(OCRResult.image_id).distinct().subquery()
        images = Image.query.filter(Image.id.notin_(images_with_ocr)).all()
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return

    total = len(images)
    processed = 0
    errors = 0

    for image in images:
        try:
            if not image or not hasattr(image, 'filepath'):
                logger.error("Invalid image object encountered")
                errors += 1
                continue

            image_path = get_image_path(image.filepath)
            if not image_path:
                errors += 1
                continue

            img, _ = process_image_file(image_path)
            if not img:
                errors += 1
                continue

            # OCR processing
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(img, config=custom_config)
            
            if not isinstance(text, str):
                text = str(text) if text else "No text detected"

            # Confidence calculation
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            confidences = [float(c) for c in data.get('conf', []) if isinstance(c, (int, float)) and c != -1]
            avg_confidence = round(sum(confidences)/len(confidences), 2) if confidences else 0.0

            # Database operations
            ocr_result = OCRResult(
                image_id=image.id,
                text=text.strip(),
                confidence=avg_confidence,
                language='eng',
                version=get_tesseract_simple_version(),
                created_at=datetime.utcnow()
            )
            
            db.session.add(ocr_result)
            db.session.commit()
            
            processed += 1
            logger.info(f"[{processed}/{total}] Processed image {image.id}")
            
        except Exception as e:
            db.session.rollback()
            errors += 1
            logger.error(f"Error processing image {image.id if image else 'unknown'}: {str(e)}")
            continue

    logger.info(f"OCR processing complete. Success: {processed}, Errors: {errors}, Total: {total}")

def register_commands(app):
    @app.cli.command("generate-ocr")
    def generate_ocr_command():
        """Generate OCR text for all images"""
        generate_ocr_for_all_images()
