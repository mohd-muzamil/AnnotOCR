from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from models import Users
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Users.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid username or password', 'danger')  # Changed to 'danger' for red alert
            return redirect(url_for('auth.login'))
            
        # Update last login timestamp
        from datetime import datetime
        from app import db
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user)
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
