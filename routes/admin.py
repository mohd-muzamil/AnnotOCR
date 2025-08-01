# routes/admin.py
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from models import Users, Studies, Images
from flask import request
from flask import abort
from services.study_splitter import split_study_into_batches, merge_batch_studies_back, delete_batch_studies
import logging
logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users')
def users():
    from flask_login import current_user
    if not current_user.is_authenticated:
        from flask import flash, redirect, url_for
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('auth.login'))
    # Ensure reviewers only see their own profile
    if current_user.role == 'admin':
        users = Users.query.all()
    else:
        users = [current_user]
    return render_template('admin/users.html', users=users)
    
@admin_bp.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        abort(403)
    from flask import request, flash, redirect, url_for
    from models.studies import Studies
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'reviewer')
        study_ids = request.form.getlist('studies[]')  # Get list of selected study IDs
        
        # Validation
        if not all([username, password, confirm_password]):
            flash('Username and password fields are required.', 'danger')
            return redirect(url_for('admin.create_user'))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('admin.create_user'))
            
        # Check if user already exists
        existing_user = Users.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken.', 'danger')
            return redirect(url_for('admin.create_user'))
            
        # Check if email is already in use
        if email:
            existing_email = Users.query.filter_by(email=email).first()
            if existing_email:
                flash('Email already in use.', 'danger')
                return redirect(url_for('admin.create_user'))
            
        # Create new user
        email_value = email if email else None
        new_user = Users(username=username, email=email_value, role=role)
        from werkzeug.security import generate_password_hash
        new_user.password_hash = generate_password_hash(password)  # Hash the password
        from app import db  # Import db to add and commit the user
        try:
            db.session.add(new_user)
            db.session.flush()  # Flush to get the user ID
            
            # Assign studies to the user if they are a reviewer
            if role == 'reviewer' and study_ids:
                studies = Studies.query.filter(Studies.id.in_(study_ids)).all()
                new_user.studies = studies
                
            db.session.commit()
            flash(f'User {username} created successfully.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
            return redirect(url_for('admin.create_user'))
        
    studies = Studies.query.all()
    return render_template('admin/create_user.html', studies=studies)

@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    from flask import request, flash, redirect, url_for
    from models.studies import Studies
    user = Users.query.get_or_404(user_id)
    
    # Strictly enforce that reviewers can only edit their own profile
    if current_user.role != 'admin' and current_user.id != user_id:
        abort(403)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'reviewer')
        study_ids = request.form.getlist('studies[]')  # Get list of selected study IDs
        
        # Validation
        if current_user.role == 'admin':
            if not username:
                flash('Username is required.', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
                
            # Check if username is taken by another user
            existing_user = Users.query.filter_by(username=username).filter(Users.id != user_id).first()
            if existing_user:
                flash('Username already taken.', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
                
        if password and password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
            
        # Check if email is taken by another user
        if email:
            existing_email = Users.query.filter_by(email=email).filter(Users.id != user_id).first()
            if existing_email:
                flash('Email already in use.', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            
        # Update user
        if current_user.role == 'admin':
            user.username = username
            # Prevent any admin user from being downgraded to reviewer
            if user.role == 'admin' and role != 'admin':
                flash('Admin accounts cannot be downgraded to reviewer.', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            user.role = role
        user.email = email if email else None
        # Reviewers can only update their own password, not for admin users or others
        if password and (current_user.role == 'admin' or (current_user.id == user.id and user.role != 'admin')):
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(password)
        from app import db
        try:
            # Assign studies to the user if they are a reviewer
            if current_user.role == 'admin' and role == 'reviewer' and study_ids:
                studies = Studies.query.filter(Studies.id.in_(study_ids)).all()
                user.studies = studies
            elif current_user.role == 'admin' and role != 'reviewer':
                user.studies = []  # Clear studies if role is not reviewer
                
            db.session.commit()
            flash(f'User {username} updated successfully.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        
    studies = Studies.query.all()
    return render_template('admin/edit_user.html', user=user, studies=studies)

@admin_bp.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        abort(403)
    from flask import flash, redirect, url_for
    user = Users.query.get_or_404(user_id)
    
    if user.username == 'admin':
        flash('The main admin account cannot be deleted.', 'danger')
        return redirect(url_for('admin.users'))
        
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
        
    from app import db
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} deleted successfully.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/studies', methods=['GET'])
def studies():
    from flask_login import current_user
    if not current_user.is_authenticated:
        from flask import flash, redirect, url_for
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('auth.login'))
    if current_user.role != 'admin':
        from flask import flash, redirect, url_for
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    from models import Studies
    from app import db
    studies = Studies.query.all()
    study_stats = []
    for study in studies:
        try:
            # Direct query for total images
            total_images_query = db.session.execute(
                "SELECT COUNT(*) FROM images WHERE study_id = :study_id",
                {"study_id": study.id}
            )
            total_images = total_images_query.scalar() or 0
            # print(f"Study {study.name} - Total Images Query Result: {total_images}")

            # Direct query for images with OCR
            images_with_ocr_query = db.session.execute(
                """
                SELECT COUNT(DISTINCT o.image_id)
                FROM ocr_results o
                WHERE o.image_id IN (
                    SELECT i.id FROM images i WHERE i.study_id = :study_id
                )
                """,
                {"study_id": study.id}
            )
            images_with_ocr = images_with_ocr_query.scalar() or 0
            # print(f"Study {study.name} - Images with OCR Query Result: {images_with_ocr}")

            # Direct query for images with corrections
            images_with_correction = 0
            try:
                images_with_correction_query = db.session.execute(
                    """
                    SELECT COUNT(DISTINCT c.image_id)
                    FROM corrections c
                    WHERE c.image_id IN (
                        SELECT i.id FROM images i WHERE i.study_id = :study_id
                    )
                    """,
                    {"study_id": study.id}
                )
                images_with_correction = images_with_correction_query.scalar() or 0
                # print(f"Study {study.name} - Images with Correction Query Result: {images_with_correction}")
            except Exception as e:
                # print(f"Could not query Corrections for study {study.name}: {str(e)}")
                pass

            # Direct query for status counts
            status_counts_query = db.session.execute(
                """
                SELECT status, COUNT(*)
                FROM images
                WHERE study_id = :study_id
                GROUP BY status
                """,
                {"study_id": study.id}
            )
            status_counts = status_counts_query.fetchall()
            status_dict = dict(status_counts) if status_counts else {}
            # print(f"Study {study.name} - Status Counts Query Result: {status_dict}")

            study_stats.append({
                'study': study,
                'total_images': total_images,
                'images_with_ocr': images_with_ocr,
                'images_with_correction': images_with_correction,
                'status_counts': status_dict
            })
        except Exception as e:
            # print(f"Error processing stats for study {study.name}: {str(e)}")
            study_stats.append({
                'study': study,
                'total_images': 0,
                'images_with_ocr': 0,
                'images_with_correction': 0,
                'status_counts': {}
            })
    return render_template('admin/studies.html', study_stats=study_stats)

@admin_bp.route('/create_study', methods=['GET', 'POST'])
@login_required
def create_study():
    if current_user.role != 'admin':
        abort(403)
    from flask import request, flash, redirect, url_for
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Study name is required.', 'danger')
            return redirect(url_for('admin.create_study'))
            
        existing_study = Studies.query.filter_by(name=name).first()
        if existing_study:
            flash('Study name already exists.', 'danger')
            return redirect(url_for('admin.create_study'))
            
        new_study = Studies(name=name, description=description)
        from app import db
        try:
            db.session.add(new_study)
            db.session.commit()
            # Create study directory in static/images/
            import os
            from os.path import join, exists
            from os import makedirs
            study_dir = join('static', 'images', name)
            if not exists(study_dir):
                try:
                    makedirs(study_dir)
                except PermissionError as e:
                    flash(f'Study {name} created successfully, but could not create directory due to permission issues: {str(e)}. Please create the directory manually or adjust permissions.', 'warning')
                    return redirect(url_for('admin.manage_study', study_id=study_id))
            flash(f'Study {name} created successfully.', 'success')
            return redirect(url_for('admin.studies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating study: {str(e)}', 'danger')
            return redirect(url_for('admin.create_study'))
            
    return render_template('admin/create_study.html')


@admin_bp.route('/upload_images/<int:study_id>', methods=['GET', 'POST'])
@login_required
def upload_images(study_id):
    if current_user.role != 'admin':
        abort(403)
    study = Studies.query.get_or_404(study_id)
    from flask import request, flash, redirect, url_for
    if request.method == 'POST':
        if 'images' not in request.files:
            flash('No images uploaded.', 'danger')
            return redirect(url_for('admin.upload_images', study_id=study_id))
            
        images = request.files.getlist('images')
        from services.data_loader import process_uploaded_images
        try:
            processed_count, errors = process_uploaded_images(images, study)
            if errors:
                for error in errors:
                    flash(error, 'danger')
            flash(f'Uploaded {processed_count} images for study {study.name}.', 'success')
            return redirect(url_for('admin.manage_study', study_id=study_id))
        except Exception as e:
            flash(f'Error processing images: {str(e)}', 'danger')
            return redirect(url_for('admin.upload_images', study_id=study_id))
            
    return render_template('admin/upload_images.html', study=study)

    

@admin_bp.route('/delete_study/<int:study_id>', methods=['POST'])
@login_required
def delete_study(study_id):
    if current_user.role != 'admin':
        abort(403)
    from flask import flash, redirect, url_for
    study = Studies.query.get_or_404(study_id)
    from app import db
    try:
        # Delete all participants associated with this study
        for participant in study.participants:
            # Delete all images associated with this participant
            for image in participant.images:
                # Delete related OCRResults records first to avoid integrity errors
                from models import OCRResults
                OCRResults.query.filter_by(image_id=image.id).delete()
                db.session.delete(image)
            db.session.delete(participant)
        # Now delete the study
        db.session.delete(study)
        db.session.commit()
        # Delete the associated folder in static/images/
        import os
        import shutil
        study_dir = os.path.join('static', 'images', study.name)
        if os.path.exists(study_dir):
            shutil.rmtree(study_dir)
        flash(f'Study {study.name} and all associated participants and images deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting study {study.name}: {str(e)}', 'danger')
    return redirect(url_for('admin.studies'))

@admin_bp.route('/manage_study/<int:study_id>', methods=['GET', 'POST'])
@login_required
def manage_study(study_id):
    if current_user.role != 'admin':
        abort(403)

    study = Studies.query.get_or_404(study_id)
    from flask import request, flash, redirect, url_for
    from models import Images, OCRResults, Corrections
    from app import db

    if request.method == 'POST':
        # Handle JSON requests (AJAX OCR processing)
        if request.is_json:
            data = request.get_json()
            action = data.get('action')
            if action and 'trigger_ocr' in action:
                image_ids = data.get('image_ids', [])
                
                # Import the OCR processing task
                try:
                    from services.tasks import process_ocr_task
                except ImportError:
                    logger.error("OCR task module not found")
                    return jsonify({'success': False, 'message': 'OCR processing is not available'}), 500

                try:
                    if action == 'trigger_ocr_selected':
                        if not image_ids:
                            return jsonify({'success': False, 'message': 'No images selected for OCR.'}), 400
                        process_ocr_task.delay(image_ids=image_ids)
                        return jsonify({'success': True, 'message': f'OCR processing started for {len(image_ids)} selected images.'})

                    elif action == 'trigger_ocr_all_images':
                        all_image_ids = [image.id for image in study.images]
                        if not all_image_ids:
                            return jsonify({'success': False, 'message': 'No images in the study to process.'}), 400
                        process_ocr_task.delay(study_id=study.id)
                        return jsonify({'success': True, 'message': 'OCR processing started for all images in the study.'})

                    elif action == 'trigger_ocr_unprocessed':
                        # Find images without OCR results
                        from models import OCRResults
                        images_with_ocr_subquery = db.session.query(Images.id).join(OCRResults).filter(Images.study_id == study.id)
                        unprocessed_images = Images.query.filter(
                            Images.study_id == study.id,
                            ~Images.id.in_(images_with_ocr_subquery)
                        ).all()
                        if not unprocessed_images:
                            return jsonify({'success': True, 'message': 'No unprocessed images to OCR.'})
                        unprocessed_image_ids = [image.id for image in unprocessed_images]
                        process_ocr_task.delay(image_ids=unprocessed_image_ids)
                        return jsonify({'success': True, 'message': f'OCR processing started for {len(unprocessed_image_ids)} unprocessed images.'})
                        
                except Exception as e:
                    logger.error(f"Error triggering OCR action '{action}': {e}")
                    return jsonify({'success': False, 'message': 'An internal error occurred while starting the task.'}), 500
        
        # Handle standard form requests
        action = request.form.get('action')
        if action and 'trigger_ocr' in action:
            image_ids = request.form.getlist('image_ids[]')

            # Import the OCR processing task
            try:
                from services.tasks import process_ocr_task
            except ImportError:
                logger.error("OCR task module not found")
                flash('OCR processing is not available', 'danger')
                return redirect(url_for('admin.manage_study', study_id=study.id))

            try:
                if action == 'trigger_ocr_selected':
                    if not image_ids:
                        flash('No images selected for OCR.', 'warning')
                        return redirect(url_for('admin.manage_study', study_id=study.id))
                    process_ocr_task.delay(image_ids=image_ids)
                    flash(f'OCR processing started for {len(image_ids)} selected images.', 'success')

                elif action == 'trigger_ocr_all_images':
                    all_image_ids = [image.id for image in study.images]
                    if not all_image_ids:
                        flash('No images in the study to process.', 'warning')
                        return redirect(url_for('admin.manage_study', study_id=study.id))
                    process_ocr_task.delay(study_id=study.id)
                    flash('OCR processing started for all images in the study.', 'success')

                elif action == 'trigger_ocr_unprocessed':
                    # Find images without OCR results
                    from models import OCRResults
                    images_with_ocr_subquery = db.session.query(Images.id).join(OCRResults).filter(Images.study_id == study.id)
                    unprocessed_images = Images.query.filter(
                        Images.study_id == study.id,
                        ~Images.id.in_(images_with_ocr_subquery)
                    ).all()
                    if not unprocessed_images:
                        flash('No unprocessed images to OCR.', 'info')
                        return redirect(url_for('admin.manage_study', study_id=study.id))
                    unprocessed_image_ids = [image.id for image in unprocessed_images]
                    process_ocr_task.delay(image_ids=unprocessed_image_ids)
                    flash(f'OCR processing started for {len(unprocessed_image_ids)} unprocessed images.', 'success')
            except Exception as e:
                logger.error(f"Error triggering OCR action '{action}': {e}")
                flash('An internal error occurred while starting the task.', 'danger')
            
            return redirect(url_for('admin.manage_study', study_id=study.id))

        # Handle standard synchronous form submissions
        image_ids = request.form.getlist('image_ids')
        if action == 'delete_selected':
            if not image_ids:
                flash('No images selected for deletion.', 'warning')
            else:
                Images.query.filter(Images.id.in_(image_ids)).delete(synchronize_session=False)
                db.session.commit()
                flash(f'{len(image_ids)} images have been deleted.', 'success')
        
        elif action == 'split_study':
            batch_size = request.form.get('batch_size', type=int)
            if batch_size and batch_size > 0:
                try:
                    created_studies = split_study_into_batches(study.id, batch_size)
                    if created_studies:
                        flash(f'Study has been split into {len(created_studies)} batches of {batch_size} participants each.', 'success')
                    else:
                        flash('No new studies were created (they may already exist).', 'info')
                    return redirect(url_for('admin.studies'))
                except Exception as e:
                    logger.error(f"Error splitting study: {e}")
                    db.session.rollback()  # Ensure session is rolled back on error
                    flash(f'Error splitting study: {str(e)}', 'danger')
            else:
                flash('Invalid batch size.', 'danger')
        
        elif action == 'merge_batch_studies':
            try:
                merged_count, batch_count = merge_batch_studies_back(study.id)
                flash(f'Successfully merged {merged_count} participants from {batch_count} batch studies back to the main study.', 'success')
                return redirect(url_for('admin.manage_study', study_id=study.id))
            except Exception as e:
                logger.error(f"Error merging batch studies: {e}")
                db.session.rollback()
                flash(f'Error merging batch studies: {str(e)}', 'danger')
        
        elif action == 'delete_batch_studies':
            try:
                deleted_studies = delete_batch_studies(study.id)
                if deleted_studies:
                    flash(f'Successfully deleted {len(deleted_studies)} empty batch studies: {", ".join(deleted_studies)}', 'success')
                else:
                    flash('No empty batch studies found to delete.', 'info')
                return redirect(url_for('admin.manage_study', study_id=study.id))
            except Exception as e:
                logger.error(f"Error deleting batch studies: {e}")
                db.session.rollback()
                flash(f'Error deleting batch studies: {str(e)}', 'danger')
        
        return redirect(url_for('admin.manage_study', study_id=study.id))

    # GET request handling
    page = request.args.get('page', 1, type=int)
    image_search_query = request.args.get('image_search', '')
    images_query = Images.query.filter_by(study_id=study.id)
    if image_search_query:
        images_query = images_query.filter(Images.filename.ilike(f'%{image_search_query}%'))
    
    images_pagination = images_query.order_by(Images.filename).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template('admin/manage_studies.html',
                           study=study,
                           images_pagination=images_pagination,
                           image_search_query=image_search_query)

@admin_bp.route('/reload_images_from_static', methods=['POST'])
@login_required
def reload_images_from_static():
    if current_user.role != 'admin':
        abort(403)
    from flask import flash, redirect, url_for
    from services.data_loader import load_images_from_static
    try:
        load_images_from_static()
        flash('Images reloaded from static directory into database.', 'success')
    except Exception as e:
        flash(f'Error reloading images: {str(e)}', 'danger')
    return redirect(url_for('admin.studies'))

@admin_bp.route('/reload_images_for_study/<int:study_id>', methods=['POST'])
@login_required
def reload_images_for_study(study_id):
    if current_user.role != 'admin':
        abort(403)
    from flask import flash, redirect, url_for
    study = Studies.query.get_or_404(study_id)
    from services.data_loader import load_images_from_static
    try:
        # Call with a specific study to reload only that study's images
        load_images_from_static(study_name=study.name)
        flash(f'Images reloaded for study {study.name} from static directory into database.', 'success')
    except Exception as e:
        flash(f'Error reloading images for study {study.name}: {str(e)}', 'danger')
    return redirect(url_for('admin.studies'))

@admin_bp.route('/sync_images_from_remote/<int:study_id>', methods=['POST'])
@login_required
def sync_images_from_remote(study_id):
    if current_user.role != 'admin':
        abort(403)
    from flask import flash, redirect, url_for
    study = Studies.query.get_or_404(study_id)
    study_name = study.name  # Store the name to avoid accessing detached instance in error handling
    try:
        from services.tasks import sync_images_task
        task = sync_images_task.delay(study_id=study_id)
        flash(f'Image sync for study {study_name} started in the background. Check logs for status.', 'info')
    except Exception as e:
        flash(f'Error starting image sync for study {study_name}: {str(e)}. Ensure Celery worker is running and aware of services.tasks module.', 'danger')
    return redirect(url_for('admin.manage_study', study_id=study_id))

@admin_bp.route('/sync_all_images_from_remote', methods=['POST'])
@login_required
def sync_all_images_from_remote():
    if current_user.role != 'admin':
        abort(403)
    from flask import flash, redirect, url_for
    try:
        from services.tasks import sync_images_task
        task = sync_images_task.delay()
        flash('Image sync for all studies started in the background. Check logs for status.', 'info')
    except Exception as e:
        flash(f'Error starting image sync across all studies: {str(e)}. Ensure Celery worker is running and aware of services.tasks module.', 'danger')
    return redirect(url_for('admin.studies'))

@admin_bp.route('/export_study/<int:study_id>', methods=['GET'])
@login_required
def export_study(study_id):
    if current_user.role != 'admin':
        abort(403)
    from flask import Response
    import pandas as pd
    from io import BytesIO
    from models import Studies, Images, OCRResults, Corrections
    from app import db
    
    study = Studies.query.get_or_404(study_id)
    
    # Fetch study stats
    total_images_query = db.session.execute(
        "SELECT COUNT(*) FROM images WHERE study_id = :study_id",
        {"study_id": study.id}
    )
    total_images = total_images_query.scalar() or 0
    
    images_with_ocr_query = db.session.execute(
        """
        SELECT COUNT(DISTINCT o.image_id)
        FROM ocr_results o
        WHERE o.image_id IN (
            SELECT i.id FROM images i WHERE i.study_id = :study_id
        )
        """,
        {"study_id": study.id}
    )
    images_with_ocr = images_with_ocr_query.scalar() or 0
    
    images_with_correction_query = db.session.execute(
        """
        SELECT COUNT(DISTINCT c.image_id)
        FROM corrections c
        WHERE c.image_id IN (
            SELECT i.id FROM images i WHERE i.study_id = :study_id
        )
        """,
        {"study_id": study.id}
    )
    images_with_correction = images_with_correction_query.scalar() or 0
    
    status_counts_query = db.session.execute(
        """
        SELECT status, COUNT(*)
        FROM images
        WHERE study_id = :study_id
        GROUP BY status
        """,
        {"study_id": study.id}
    )
    status_counts = dict(status_counts_query.fetchall() or [])
    
    # Create stats DataFrame
    stats_data = {
        'Metric': ['Total Images', 'Images with OCR', 'Images with Correction'],
        'Value': [total_images, images_with_ocr, images_with_correction]
    }
    for status, count in status_counts.items():
        stats_data['Metric'].append(f'Status: {status}')
        stats_data['Value'].append(count)
    stats_df = pd.DataFrame(stats_data)
    
    # Fetch detailed data for images
    images = Images.query.filter_by(study_id=study_id).all()
    detailed_data = []
    for img in images:
        ocr_result = OCRResults.query.filter_by(image_id=img.id).first()
        correction = Corrections.query.filter_by(image_id=img.id).first()
        detailed_data.append({
            'Filename': img.filename,
            'Original OCR': ocr_result.text if ocr_result else '',
            'Corrected OCR': correction.corrected_text if correction else '',
            'OCR Status': img.status or 'Pending'
        })
    detailed_df = pd.DataFrame(detailed_data)
    
    # Write to Excel with two sheets
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        stats_df.to_excel(writer, sheet_name='Stats', index=False)
        detailed_df.to_excel(writer, sheet_name='Detailed Data', index=False)
    
    output.seek(0)
    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={study.name}_report.xlsx"}
    )

# Temporary test route outside /admin prefix to check if prefix is causing logout
from flask import Blueprint
test_bp = Blueprint('test', __name__, url_prefix='/test')

@test_bp.route('/admin-access', methods=['GET'])
def test_admin_access():
    from flask_login import current_user
    if not current_user.is_authenticated:
        from flask import flash, redirect, url_for
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('auth.login'))
    if current_user.role != 'admin':
        from flask import flash, redirect, url_for
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    from flask import render_template
    return render_template('admin/studies.html', studies=Studies.query.all())
