# routes/study.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from models import Studies, Participants
from extensions import db

study_bp = Blueprint('study', __name__, url_prefix='/study')

@study_bp.route('/create', methods=['GET', 'POST'])
# @login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        study = Study(name=name, description=description)
        db.session.add(study)
        db.session.commit()
        
        flash('Study created successfully', 'success')
        return redirect(url_for('dashboard.study', study_id=study.id))
    
    return render_template('study/create.html')

@study_bp.route('/<int:study_id>/add_participant', methods=['POST'])
# @login_required
def add_participant(study_id):
    identifier = request.form.get('identifier')
    
    participant = Participant(identifier=identifier, study_id=study_id)
    db.session.add(participant)
    db.session.commit()
    
    flash('Participant added successfully', 'success')
    return redirect(url_for('dashboard.study', study_id=study_id))