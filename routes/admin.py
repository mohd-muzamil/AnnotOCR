# routes/admin.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Users
from models import Studies
from flask import abort


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# @admin_bp.route('/users')
# @login_required
# def users():
#     if not current_user.is_admin:
#         abort(403)
#     users = Users.query.all()
#     return render_template('admin/users.html', users=users)

@admin_bp.route('/users')
# @login_required
def users():
    print(f"User admin status: {getattr(current_user, 'is_admin', None)}")
    # Temporarily disable 403 to check if route works
    # if not current_user.is_admin:
    #     abort(403)
    users = Users.query.all()
    return render_template('admin/users.html', users=users)
    
@admin_bp.route('/create_user', methods=['GET', 'POST'])
# @login_required
def create_user():
    # Temporarily disable admin check for testing
    # if not current_user.is_admin:
    #     abort(403)
    from flask import request, flash, redirect, url_for
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'reviewer')
        
        # Validation
        if not all([username, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin.create_user'))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('admin.create_user'))
            
        # Check if user already exists
        existing_user = Users.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken.', 'danger')
            return redirect(url_for('admin.create_user'))
            
        # Create new user
        new_user = Users(username=username, role=role)
        from werkzeug.security import generate_password_hash
        new_user.password_hash = generate_password_hash(password)  # Hash the password
        from app import db  # Import db to add and commit the user
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('admin.users'))
        
    return render_template('admin/create_user.html')

