from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Studies, Participants, Images, OCRResults, Corrections
from extensions import db
from services.ocr_cleaner import clean_ocr_text
from services.text_validator import validate_corrected_text

review_bp = Blueprint('review', __name__, url_prefix='/review')

@review_bp.route('/study/<string:study_name>/participant/<string:participant_name>')
@login_required
def participant_review(study_name, participant_name):
    study = Studies.query.filter_by(name=study_name).first_or_404()
    participant = Participants.query.filter_by(
        name=participant_name, 
        study_id=study.id
    ).first_or_404()
    
    # Get images with their OCR results and corrections
    images = Images.query.filter_by(
        participant_id=participant.id
    ).options(
        db.joinedload(Images.ocr_results),
        db.joinedload(Images.corrections)
    ).order_by(Images.upload_time.asc()).all()
    
    image_data = []
    for image in images:
        # Get original OCR text
        ocr_text = ''
        ocr_result_id = None
        
        if image.ocr_results:
            if isinstance(image.ocr_results, list):
                if image.ocr_results:  # Check if list is not empty
                    ocr_text = image.ocr_results[0].text
                    ocr_result_id = image.ocr_results[0].id
            else:
                # Single OCRResults object
                ocr_text = image.ocr_results.text
                ocr_result_id = image.ocr_results.id
        
        # Get latest corrected text, or use cleaned OCR text if no correction exists
        corrected_text = ''
        if image.corrections:
            latest_correction = max(image.corrections, key=lambda x: x.corrected_at)
            corrected_text = latest_correction.corrected_text
        elif ocr_text:
            corrected_text = clean_ocr_text(ocr_text)
        
        image_data.append({
            'id': image.id,
            'filepath': image.filepath,
            'status': image.status,
            'ocr_text': ocr_text,
            'corrected_text': corrected_text,
            'ocr_result_id': ocr_result_id
        })
    
    return render_template('review/batch.html',
        study=study,
        participant=participant,
        images=image_data,
        approved_count=participant.approved_count,
        rejected_count=sum(1 for img in participant.images if img.status == 'rejected'),
        pending_count=sum(1 for img in participant.images if img.status == 'pending'),
        image_count=len(participant.images)
    )


@review_bp.route('/batch/submit', methods=['POST'])
@login_required
def batch_submit():
    data = request.get_json()
    
    try:
        image = Images.query.get(data['image_id'])
        if not image:
            return jsonify({'success': False, 'error': 'Image not found'}), 404
        
        # Get original OCR text and ID
        ocr_text = ''
        ocr_result_id = None
        if image.ocr_results:
            if isinstance(image.ocr_results, list):
                if image.ocr_results:  # Check if list is not empty
                    ocr_text = image.ocr_results[0].text
                    ocr_result_id = image.ocr_results[0].id
            else:
                # Single OCRResults object
                ocr_text = image.ocr_results.text
                ocr_result_id = image.ocr_results.id
        
        # Update image status
        if 'status' in data:
            image.status = data['status']
        
        # Validate corrected text before saving
        corrected_text = data.get('corrected_text', '')
        is_valid, error_message = validate_corrected_text(corrected_text)
        if not is_valid:
            return jsonify({'success': False, 'error': f'Invalid format: {error_message}'}), 400
        
        # Create new correction
        correction = Corrections(
            original_text=ocr_text,
            corrected_text=corrected_text,
            status=data.get('status', 'pending'),
            user_id=current_user.id,
            image_id=image.id,
            ocr_result_id=ocr_result_id
        )
        db.session.add(correction)
        
        # Update app suggestions based on corrected text
        update_app_suggestions(corrected_text)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def update_app_suggestions(corrected_text):
    """
    Update the app suggestions JSON file with new terms from the corrected text.
    Split the text by commas and newlines to extract potential app names.
    """
    import json
    import os
    
    suggestions_file = 'static/data/app_suggestions.json'
    
    if not corrected_text:
        return
    
    try:
        # Load existing suggestions
        with open(suggestions_file, 'r') as file:
            data = json.load(file)
            existing_apps = data.get('apps', [])
        
        # Extract potential new app names by splitting on commas and newlines
        potential_apps = []
        # Split by newlines first
        lines = corrected_text.replace('\r', '\n').split('\n')
        for line in lines:
            line = line.strip()
            if line and ',' in line:
                # Take only the part before the first comma as the app name
                app_name = line.split(',')[0].strip('.;:"\'').capitalize()
                if (app_name and len(app_name) > 2 and app_name not in existing_apps and 
                    app_name not in potential_apps and any(char.isalpha() for char in app_name)):
                    potential_apps.append(app_name)
            elif line:
                # If no comma, consider the whole line as a potential app name
                app_name = line.strip('.;:"\'').capitalize()
                if (app_name and len(app_name) > 2 and app_name not in existing_apps and 
                    app_name not in potential_apps and any(char.isalpha() for char in app_name)):
                    potential_apps.append(app_name)
        
        # Add new apps to the list
        if potential_apps:
            data['apps'].extend(potential_apps)
            with open(suggestions_file, 'w') as file:
                json.dump(data, file, indent=2)
            print(f"Updated app suggestions with: {potential_apps}")
        
    except Exception as e:
        print(f"Error updating app suggestions: {e}")
