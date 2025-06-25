from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Studies, Participants, Images, OCRResults, Corrections
from extensions import db
from services.ocr_cleaner import clean_ocr_text
from services.text_validator import validate_corrected_text

review_bp = Blueprint('review', __name__, url_prefix='/annotation/review')

@review_bp.route('/study/<string:study_name>/participant/<string:participant_name>')
@login_required
def participant_review(study_name, participant_name):
    study = Studies.query.filter_by(name=study_name).first_or_404()
    participant = Participants.query.filter_by(
        name=participant_name, 
        study_id=study.id
    ).first_or_404()
    
    # Get images with their OCR results
    images = Images.query.filter_by(
        participant_id=participant.id
    ).options(
        db.joinedload(Images.ocr_results)
    ).order_by(Images.upload_time.asc()).all()
    
    # Manually query corrections to avoid schema mismatch issues
    from sqlalchemy import select
    correction_data = {}
    try:
        corrections_query = select(
            Corrections.image_id,
            Corrections.corrected_text,
            Corrections.created_at
        ).where(Corrections.image_id.in_([img.id for img in images])).order_by(Corrections.created_at.desc())
        corrections_result = db.session.execute(corrections_query).all()
        for corr in corrections_result:
            image_id = corr[0]
            if image_id not in correction_data or correction_data[image_id]['created_at'] < corr[2]:
                correction_data[image_id] = {
                    'corrected_text': corr[1],
                    'created_at': corr[2]
                }
    except Exception as e:
        logger.error(f"Error querying corrections: {e}")
        correction_data = {}
    
    image_data = []
    for image in images:
        # Get original OCR text - preserve exact output from Pytesseract as requested
        ocr_text = ''
        ocr_result_id = None
        
        if image.ocr_results:
            if image.ocr_results:  # Check if list is not empty
                ocr_text = image.ocr_results[0].text
                ocr_result_id = image.ocr_results[0].id
        
        # Get latest corrected text, or use raw OCR text if no correction exists
        corrected_text = ''
        if image.id in correction_data:
            corrected_text = correction_data[image.id]['corrected_text']
        elif ocr_text:
            corrected_text = ocr_text
        
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
        approved_count=sum(1 for img in participant.images if img.status == 'approved'),
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
            if image.ocr_results:  # Check if list is not empty
                ocr_text = image.ocr_results[0].text
                ocr_result_id = image.ocr_results[0].id
        
        # Update image status
        if 'status' in data:
            image.status = data['status']
        
        # Validate corrected text before saving
        corrected_text = data.get('corrected_text', '')
        is_valid, error_message = validate_corrected_text(corrected_text)
        if not is_valid:
            return jsonify({'success': False, 'error': f'Invalid format: {error_message}'}), 400
        
        # Create new correction
        # Note: original_text and status might not be in the database schema yet.
        # Only include them if the database has been migrated.
        correction_kwargs = {
            'corrected_text': corrected_text,
            'user_id': current_user.id,
            'image_id': image.id,
            'ocr_result_id': ocr_result_id
        }
        try:
            # Attempt to add new fields only if they exist in the model and database
            correction_kwargs['original_text'] = ocr_text
            correction_kwargs['status'] = data.get('status', 'pending')
        except Exception as e:
            logger.warning(f"Could not set original_text or status for Corrections: {e}")
        correction = Corrections(**correction_kwargs)
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
                    app_name not in potential_apps and any(char.isalpha() for char in app_name) and
                    not app_name.startswith('Down by') and not app_name.startswith('Up by')):
                    potential_apps.append(app_name)
            elif line:
                # If no comma, consider the whole line as a potential app name
                app_name = line.strip('.;:"\'').capitalize()
                if (app_name and len(app_name) > 2 and app_name not in existing_apps and 
                    app_name not in potential_apps and any(char.isalpha() for char in app_name) and
                    not app_name.startswith('Down by') and not app_name.startswith('Up by')):
                    potential_apps.append(app_name)
        
        # Add new apps to the list, ensuring no case-insensitive duplicates
        if potential_apps:
            initial_count = len(data['apps'])
            # Convert existing apps to lowercase for comparison
            existing_apps_lower = {app.lower() for app in data['apps']}
            unique_new_apps = []
            for app in potential_apps:
                if app.lower() not in existing_apps_lower:
                    unique_new_apps.append(app)
                    existing_apps_lower.add(app.lower())
            data['apps'].extend(unique_new_apps)
            new_count = len(data['apps'])
            if new_count > initial_count:
                try:
                    with open(suggestions_file, 'w') as file:
                        json.dump(data, file, indent=2)
                    # Removed print statement for successful app suggestions update
                    pass
                except PermissionError as pe:
                    # Removed print statement for permission error
                    pass
                except Exception as we:
                    # Removed print statement for error writing app suggestions
                    pass
            else:
                # Removed print statement for no new unique app suggestions
                pass
        
    except Exception as e:
        # Removed print statement for error reading app suggestions
        pass
