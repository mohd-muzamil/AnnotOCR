from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from models import Studies, Participants
from extensions import db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    studies = Studies.query.options(
        db.joinedload(Studies.participants)
    ).all()
    
    # Filter studies for reviewers to only show assigned studies
    if current_user.role != 'admin':
        studies = [study for study in studies if study in current_user.studies]
    
    total_participants = sum(len(study.participants) for study in studies)
    total_images = sum(study.image_count for study in studies)
    
    # Calculate completion rate (example logic)
    approved_images = sum(study.approved_count for study in studies)
    completion_rate = round((approved_images / total_images) * 100) if total_images > 0 else 0
    
    return render_template('dashboard/index.html',
                         all_studies=studies,
                         total_participants=total_participants,
                         total_images=total_images,
                         completion_rate=completion_rate)


@dashboard_bp.route('/study/<string:study_name>')
@login_required
def study(study_name):
    study = Studies.query.filter_by(name=study_name).first_or_404()
    
    # Restrict access for reviewers to only assigned studies
    if current_user.role != 'admin' and study not in current_user.studies:
        flash('You do not have permission to access this study.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Load participants with their image counts
    participants = []
    for participant in study.participants:
        image_count = len(participant.images)
        approved_count = sum(1 for img in participant.images if img.status == 'approved')
        rejected_count = sum(1 for img in participant.images if img.status == 'rejected')
        # Calculate a summary status for OCR corrections
        correction_status = "Not Available"
        try:
            from models import Corrections
            corrected_count = sum(1 for img in participant.images if any(hasattr(c, 'image_id') and c.image_id == img.id for c in Corrections.query.all()))
            correction_status = f"Corrected: {corrected_count}/{image_count}"
        except Exception as e:
            # Removed print statement for correction status error
            pass
        participants.append({
            'participant': participant,
            'image_count': image_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'correction_status': correction_status
        })
    
    return render_template('dashboard/study.html',
                         study=study,
                         participants=participants)
