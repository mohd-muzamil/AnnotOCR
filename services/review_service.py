# services/review_service.py
# This script defines a ReviewService class that manages the review process for OCR-processed images.
# It provides methods to retrieve a queue of images needing review (those with status 'ocr_completed' or 'needs_review')
# and to submit corrections for reviewed images, updating their status based on reviewer actions (approve or reject).
# This service is essential for the quality control and validation of OCR data within the application.

from models import Image, Correction
from extensions import db

class ReviewService:
    @staticmethod
    def get_review_queue():
        # Return images that need review or are OCR completed
        return Image.query.filter(
            Image.status.in_(['ocr_completed', 'needs_review'])
        ).order_by(Image.upload_time.asc()).all()

    @staticmethod
    def submit_correction(image_id, corrected_text, action, reviewer_id):
        image = Image.query.get_or_404(image_id)
        
        # Grab original OCR text if available
        original_text = ''
        if image.ocr_results:
            original_text = image.ocr_results[0].text
        
        correction = Correction(
            image_id=image.id,
            original_text=original_text,
            corrected_text=corrected_text,
            status='approved' if action == 'approve' else 'rejected',
            user_id=reviewer_id
        )
        
        db.session.add(correction)
        
        # Update image status based on action
        if action == 'approve':
            image.status = 'approved'
        else:
            image.status = 'needs_review'
        
        db.session.commit()
        return image
