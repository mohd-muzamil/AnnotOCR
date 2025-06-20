from flask import Blueprint, render_template
from flask_login import login_required
from models import Studies, Participants
from extensions import db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/annotation')

@dashboard_bp.route('/')
@login_required
def index():
    studies = Studies.query.options(
        db.joinedload(Studies.participants)
    ).all()
    
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
    
    # Load participants with their image counts
    participants = []
    for participant in study.participants:
        participants.append({
            'participant': participant,
            'image_count': len(participant.images),
            'approved_count': sum(1 for img in participant.images if img.status == 'approved'),
            'rejected_count': sum(1 for img in participant.images if img.status == 'rejected'),
            'pending_count': sum(1 for img in participant.images if img.status == 'pending')
        })
    
    return render_template('dashboard/study.html',
                         study=study,
                         participants=participants)
