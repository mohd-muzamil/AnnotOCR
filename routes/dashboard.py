from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Studies, Participants, Images
from utils.sorting import natural_sort_key
from flask_paginate import Pagination, get_page_args
from extensions import db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    studies_query = Studies.query.options(db.joinedload(Studies.participants))
    
    if current_user.role != 'admin':
        studies_query = studies_query.join(Studies.reviewers).filter_by(id=current_user.id)

    all_studies = studies_query.all()
    study_names = {s.name for s in all_studies}

    studies_to_display = []
    for study in all_studies:
        # If a study has been split (e.g., 'GIA_1' exists), hide the original ('GIA')
        if f"{study.name}_1" not in study_names:
            studies_to_display.append(study)

    studies_data = []
    for study in studies_to_display:
        total_images = study.image_count
        reviewed_images = study.approved_count + study.rejected_count
        pending_images = total_images - reviewed_images
        completion_percent = (reviewed_images / total_images * 100) if total_images > 0 else 0

        studies_data.append({
            'study': study,
            'rejected_count': study.rejected_count,
            'pending_count': pending_images,
            'completion_percent': round(completion_percent, 1)
        })

    total_participants = sum(len(s['study'].participants) for s in studies_data)
    total_images = sum(s['study'].image_count for s in studies_data)

    total_approved = sum(s['study'].approved_count for s in studies_data)
    total_rejected = sum(s['study'].rejected_count for s in studies_data)
    total_pending = total_images - (total_approved + total_rejected)

    return render_template('dashboard/index.html',
                         studies_data=studies_data,
                         total_participants=total_participants,
                         total_images=total_images,
                         total_approved=total_approved,
                         total_rejected=total_rejected,
                         total_pending=total_pending)


@dashboard_bp.route('/study/<string:study_name>')
@login_required
def study(study_name):
    study = Studies.query.filter_by(name=study_name).first_or_404()

    if current_user.role != 'admin' and study not in current_user.studies:
        flash('You do not have permission to access this study.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Search and pagination
    search_query = request.args.get('search', '')
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')

    participants_query = Participants.query.filter_by(study_id=study.id)
    if search_query:
        participants_query = participants_query.filter(Participants.name.ilike(f'%{search_query}%'))

    # Sorting participants naturally before pagination
    all_participants = participants_query.all()
    sorted_participants = sorted(all_participants, key=lambda p: natural_sort_key(p.name))
    
    start = offset
    end = offset + per_page
    paginated_participants = sorted_participants[start:end]
    
    participants_pagination = Pagination(page=page, per_page=per_page, total=len(sorted_participants), css_framework='bootstrap5')

    # Get corrections for the paginated participants
    from models import Corrections
    all_image_ids = [img.id for p in paginated_participants for img in p.images]
    corrected_image_ids = set()
    if all_image_ids:
        corrected_image_ids = {c.image_id for c in Corrections.query.filter(Corrections.image_id.in_(all_image_ids)).all()}

    participants_data = []
    for participant in paginated_participants:
        image_count = len(participant.images)
        approved_count = sum(1 for img in participant.images if img.status == 'approved')
        rejected_count = sum(1 for img in participant.images if img.status == 'rejected')
        corrected_count = sum(1 for img in participant.images if img.id in corrected_image_ids)
        correction_status = f"Corrected: {corrected_count}/{image_count}"
        total_reviewed = approved_count + rejected_count
        progress_percent = (total_reviewed / image_count * 100) if image_count > 0 else 0

        participants_data.append({
            'participant': participant,
            'image_count': image_count,
            'correction_status': correction_status,
            'progress_percent': progress_percent
        })

    return render_template('dashboard/study.html',
                         study=study,
                         participants_data=participants_data,
                         pagination=participants_pagination,
                         search_query=search_query)
