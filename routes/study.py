# routes/study.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Studies, Participants
from extensions import db

study_bp = Blueprint('study', __name__, url_prefix='/annotation/study')

@study_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role != 'admin':
        flash('You do not have permission to create studies.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        study = Studies(name=name, description=description)
        db.session.add(study)
        db.session.commit()
        
        flash('Study created successfully', 'success')
        return redirect(url_for('dashboard.study', study_name=study.name))
    
    return render_template('study/create.html')

@study_bp.route('/<int:study_id>/add_participant', methods=['POST'])
@login_required
def add_participant(study_id):
    study = Studies.query.get_or_404(study_id)
    
    if current_user.role != 'admin' and study not in current_user.studies:
        flash('You do not have permission to add participants to this study.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    identifier = request.form.get('identifier')
    
    participant = Participants(identifier=identifier, study_id=study_id)
    db.session.add(participant)
    db.session.commit()
    
    flash('Participant added successfully', 'success')
    return redirect(url_for('dashboard.study', study_name=study.name))
