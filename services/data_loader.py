# services/data_loader.py
# This script is responsible for loading image data from a static directory structure into the application's database.
# It iterates through directories representing studies and participants, creating corresponding database entries if they do not exist.
# For each image file found, it checks if the image is already in the database before adding it with a 'pending' status.
# This service is crucial for initializing or updating the database with image data for further processing like OCR.

import os
from extensions import db
from models import Studies, Participants, Images

def load_images_from_static(study_name=None):
    image_root = os.path.join('static', 'images')
    
    if not os.path.exists(image_root):
        print(f"Image root directory {image_root} does not exist. Cannot load images.")
        return
    
    study_names = [study_name] if study_name else [d for d in os.listdir(image_root) if os.path.isdir(os.path.join(image_root, d))]
    
    for name in study_names:
        if not name or '_' in name:  # Guard against None, empty string, or already split studies
            if '_' in name:
                print(f"Skipping already split study: {name}")
            else:
                print("Encountered an empty or None study name, skipping.")
            continue

        study_path = os.path.join(image_root, name)
        if not os.path.isdir(study_path):
            print(f"Study path {study_path} is not a directory, skipping.")
            continue

        # Collect all images for the study first
        all_images_for_study = []
        for participant_id_str in os.listdir(study_path):
            participant_path = os.path.join(study_path, participant_id_str)
            if not os.path.isdir(participant_path):
                continue
            
            for filename in os.listdir(participant_path):
                if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                
                relative_path = os.path.join('images', name, participant_id_str, filename)
                all_images_for_study.append({
                    "filename": filename,
                    "filepath": relative_path,
                    "participant_id_str": participant_id_str,
                    "original_study_name": name
                })

        # If no images, continue
        if not all_images_for_study:
            continue

        # Split into batches if necessary
        if len(all_images_for_study) > 1000:
            import math
            num_batches = math.ceil(len(all_images_for_study) / 1000)
            for i in range(num_batches):
                batch_images = all_images_for_study[i*1000:(i+1)*1000]
                batch_study_name = f"{name}_{i+1}"
                process_image_batch(batch_images, batch_study_name)
        else:
            process_image_batch(all_images_for_study, name)

    print("Finished loading images into database")

def process_image_batch(images_to_process, study_name):
    # Get or create study
    study = Studies.query.filter_by(name=study_name).first()
    if not study:
        study = Studies(name=study_name)
        db.session.add(study)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error creating study {study_name}: {e}")
            return

    for image_data in images_to_process:
        participant_id_str = image_data['participant_id_str']
        filename = image_data['filename']
        relative_path = image_data['filepath']

        try:
            participant = Participants.query.filter_by(
                name=participant_id_str, 
                study_id=study.id
            ).first()
            
            if not participant:
                participant = Participants(
                    name=participant_id_str, 
                    study_id=study.id
                )
                db.session.add(participant)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error processing participant {participant_id_str} for study {study_name}: {e}")
            continue

        # Process each image
        try:
            existing = Images.query.filter_by(
                filename=filename,
                participant_id=participant.id
            ).first()
            
            if not existing:
                image = Images(
                    filename=filename,
                    filepath=relative_path,
                    participant_id=participant.id,
                    study_id=study.id,
                    status='pending'
                )
                db.session.add(image)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error processing image {filename} for study {study_name}: {e}")
            continue

def process_uploaded_images(images, study):
    """
    Process uploaded images, parse filenames to extract study and participant information,
    and save them to the appropriate directory structure.
    Returns a tuple of (processed_count, errors).
    """
    import re
    from os.path import join, exists
    from os import makedirs
    
    processed_count = 0
    errors = []
    image_root = join('static', 'images')
    
    for image in images:
        if not image.filename:
            errors.append(f"No filename provided for an uploaded image.")
            continue
            
        # Parse filename to extract study and participant info
        # Expected format: "20230525T072451Z-PROSITAIA0002-image-uploadtime-20230525T102513Z.jpg"
        match = re.search(r'(\w+?)(\d+)-image-uploadtime', image.filename)
        if not match:
            errors.append(f"Invalid filename format for {image.filename}. Expected format like '20230525T072451Z-PROSITAIA0002-image-uploadtime-20230525T102513Z.jpg'")
            continue
            
        study_prefix = match.group(1)
        participant_id = match.group(1) + match.group(2)
        
        # Create directory structure
        study_dir = join(image_root, study.name)
        participant_dir = join(study_dir, participant_id)
        try:
            if not exists(study_dir):
                makedirs(study_dir)
            if not exists(participant_dir):
                makedirs(participant_dir)
        except Exception as e:
            errors.append(f"Error creating directories for {image.filename}: {str(e)}")
            continue
            
        # Save the image to the participant directory
        destination_path = join(participant_dir, image.filename)
        try:
            image.save(destination_path)
        except Exception as e:
            errors.append(f"Error saving image {image.filename}: {str(e)}")
            continue
            
        # Check or create participant in database
        participant = Participants.query.filter_by(name=participant_id, study_id=study.id).first()
        if not participant:
            participant = Participants(name=participant_id, study_id=study.id)
            db.session.add(participant)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                errors.append(f"Error creating participant {participant_id} for {image.filename}: {str(e)}")
                continue
                
        # Add image to database
        relative_path = join('images', study.name, participant_id, image.filename)
        existing_image = Images.query.filter_by(filename=image.filename, participant_id=participant.id).first()
        if not existing_image:
            new_image = Images(
                filename=image.filename,
                filepath=relative_path,
                participant_id=participant.id,
                study_id=study.id,
                status='pending'
            )
            db.session.add(new_image)
            try:
                db.session.commit()
                processed_count += 1
            except Exception as e:
                db.session.rollback()
                errors.append(f"Error adding image {image.filename} to database: {str(e)}")
                continue
        else:
            processed_count += 1
            
    return processed_count, errors

def sync_images_from_remote_server(study_id=None):
    """
    Sync images from a remote server's Docker container to the local static/images directory.
    Images are organized into STUDY_NAME/PARTICIPANT_ID folders based on filename parsing.
    Updates the database with new studies, participants, and images.
    Returns a tuple of (new_images_count, new_studies_count, errors).
    """
    import re
    import subprocess
    import os
    from os.path import join, exists
    from os import makedirs, remove
    import tempfile
    from shutil import copyfile
    
    new_images_count = 0
    new_studies_count = 0
    errors = []
    image_root = join('static', 'images')
    remote_server = os.environ.get('REMOTE_SERVER', 'frigg2.research.cs.dal.ca')
    remote_username = os.environ.get('REMOTE_USERNAME', '')
    container_name = os.environ.get('CONTAINER_NAME', 'docker-compose_meteorapp_1')
    remote_path = os.environ.get('REMOTE_PATH', '/upload/Image')
    # Construct SSH command with username if provided
    ssh_command = f"ssh {remote_username}@{remote_server}" if remote_username else f"ssh {remote_server}"
    # Use system's default temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Check for dry run mode from environment variable
    dry_run = os.environ.get('DRY_RUN', 'false').lower() == 'true'
    if dry_run:
        errors.append("DRY_RUN mode enabled: No images will be copied, only counting potential syncs.")
    
    try:
        # Step 1: List files in the remote Docker container, filtering by study name if study_id is provided
        print(f"Starting sync for study_id: {study_id}")
        study_name_filter = ""
        if study_id:
            study = Studies.query.get(study_id)
            if study:
                study_name_filter = f"| grep {study.name}"
                print(f"Filtering for study: {study.name}")
        
        list_cmd = f"{ssh_command} 'docker exec {container_name} ls {remote_path} {study_name_filter}'"
        print(f"Executing command: {list_cmd}")
        
        try:
            result = subprocess.run(list_cmd, shell=True, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            errors.append("Timeout occurred while listing files on remote server")
            return new_images_count, new_studies_count, errors
            
        if result.returncode != 0:
            errors.append(f"Error listing files on remote server: {result.stderr}")
            return new_images_count, new_studies_count, errors
            
        remote_files = result.stdout.splitlines()
        image_files = [f for f in remote_files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if not image_files:
            errors.append("No image files found on remote server.")
            return new_images_count, new_studies_count, errors
            
        # Step 2: Get list of existing image filenames from database to avoid copying duplicates
        existing_images = set()
        if study_id:
            existing_images = set(img.filename for img in Images.query.filter_by(study_id=study_id).all())
        else:
            existing_images = set(img.filename for img in Images.query.all())
            
        images_to_copy = [img for img in image_files if img not in existing_images]
        
        print(f"Found {len(image_files)} total images, {len(existing_images)} already exist, {len(images_to_copy)} new images to copy")
        
        if not images_to_copy:
            errors.append("No new images to sync; all images are already in the database.")
            return new_images_count, new_studies_count, errors
            
        # Limit the number of images to sync in one batch to prevent hanging
        max_batch_size = 50  # Process at most 50 images per sync
        if len(images_to_copy) > max_batch_size:
            images_to_copy = images_to_copy[:max_batch_size]
            errors.append(f"Limited sync to {max_batch_size} images to prevent timeout. Run sync again to process more.")
            
        if dry_run:
            new_images_count = len(images_to_copy)
            errors.append(f"DRY_RUN: Would have synced {new_images_count} new images.")
            return new_images_count, new_studies_count, errors
            
        # Step 3: Copy only new images to a temporary local directory
        for i, image_file in enumerate(images_to_copy, 1):
            print(f"Processing image {i}/{len(images_to_copy)}: {image_file}")
            remote_file_path = f"{remote_path}/{image_file}"
            local_temp_path = join(temp_dir, image_file)
            copy_cmd = f"{ssh_command} 'docker cp {container_name}:{remote_file_path} -'"
            try:
                # Use Popen to handle binary data directly with timeout
                process = subprocess.Popen(copy_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    output, error = process.communicate(timeout=60)  # 60 second timeout per file
                except subprocess.TimeoutExpired:
                    process.kill()
                    errors.append(f"Timeout copying file {image_file} from remote server")
                    continue
                    
                if process.returncode != 0:
                    errors.append(f"Error copying file {image_file} from remote server: {error.decode('utf-8', errors='ignore')}")
                    continue
                
                # The output from 'docker cp ... -' is a tar archive, so extract the file content
                import tarfile
                from io import BytesIO
                with tarfile.open(fileobj=BytesIO(output), mode='r|') as tar:
                    member = tar.next()
                    if member is None:
                        errors.append(f"Error: No file found in tar archive for {image_file}")
                        continue
                    file_data = tar.extractfile(member).read()
                
                # Write extracted binary data to temporary file
                with open(local_temp_path, 'wb') as f:
                    f.write(file_data)
                
                # Basic integrity check: ensure file is not empty
                if os.path.getsize(local_temp_path) == 0:
                    errors.append(f"Error: Copied file {image_file} is empty after extraction.")
                    os.remove(local_temp_path)
                    continue
                
            except Exception as e:
                errors.append(f"Error copying or extracting file {image_file} from remote server: {str(e)}")
                continue
                
            # Step 4: Parse filename to extract study and participant info
            # Handle multiple filename formats:
            # Format 1: "20230812T170952Z-PROSITAIA0307-image-uploadtime-20230812T221017Z.jpg"
            # Format 2: "20091009T180920Z-PROSIT000R-image-uploadtime-20210606T235222Z.jpg"
            
            study_name = None
            participant_id = None
            
            # Try the standard format first (PROSITAIA followed by numbers)
            match = re.search(r'(PROSITAIA)(\d+)-image-uploadtime', image_file)
            if match:
                study_name = match.group(1)
                participant_id = match.group(1) + match.group(2)
            else:
                # Try the alternative format (PROSIT followed by alphanumeric)
                match = re.search(r'(PROSIT)([0-9A-Z]+)-image-uploadtime', image_file)
                if match:
                    study_name = match.group(1)
                    participant_id = match.group(1) + match.group(2)
                else:
                    # Try a more general pattern for any format with -image-uploadtime-
                    match = re.search(r'\w+-([A-Z]+\w*)-image-uploadtime', image_file)
                    if match:
                        participant_id = match.group(1)
                        # Extract study name from participant ID (remove trailing numbers/letters)
                        study_match = re.search(r'^([A-Z]+)', participant_id)
                        if study_match:
                            study_name = study_match.group(1)
                        else:
                            study_name = "UNKNOWN"
            
            if not study_name or not participant_id:
                errors.append(f"Could not parse filename format for {image_file}. Skipping this file.")
                print(f"Failed to parse: {image_file}")
                continue
                
            print(f"Parsed: {image_file} -> Study: {study_name}, Participant: {participant_id}")
            
            # Step 4: Check or create study in database
            study = Studies.query.filter_by(name=study_name).first()
            if not study:
                study = Studies(name=study_name)
                db.session.add(study)
                try:
                    db.session.commit()
                    new_studies_count += 1
                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Error creating study {study_name} for {image_file}: {str(e)}")
                    continue
                    
            # If a specific study_id is provided, skip images not belonging to this study
            if study_id and study.id != study_id:
                continue
                
            # Step 5: Create directory structure
            study_dir = join(image_root, study_name)
            participant_dir = join(study_dir, participant_id)
            try:
                if not exists(study_dir):
                    makedirs(study_dir)
                if not exists(participant_dir):
                    makedirs(participant_dir)
            except Exception as e:
                errors.append(f"Error creating directories for {image_file}: {str(e)}")
                continue
                
            # Step 6: Check or create participant in database
            participant = Participants.query.filter_by(name=participant_id, study_id=study.id).first()
            if not participant:
                participant = Participants(name=participant_id, study_id=study.id)
                db.session.add(participant)
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Error creating participant {participant_id} for {image_file}: {str(e)}")
                    continue
                    
            # Step 7: Check if image already exists in database
            existing_image = Images.query.filter_by(filename=image_file, participant_id=participant.id).first()
            if existing_image:
                continue  # Skip if image is already in database
                
            # Step 8: Copy image to final destination if it doesn't exist locally
            destination_path = join(participant_dir, image_file)
            if not exists(destination_path):
                copyfile(local_temp_path, destination_path)
                new_images_count += 1
            else:
                continue  # Skip if image file already exists locally
                
            # Step 9: Add image to database
            relative_path = join('images', study_name, participant_id, image_file)
            new_image = Images(
                filename=image_file,
                filepath=relative_path,
                participant_id=participant.id,
                study_id=study.id,
                status='pending'
            )
            db.session.add(new_image)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                errors.append(f"Error adding image {image_file} to database: {str(e)}")
                continue
                
    finally:
        # Clean up temporary directory
        for temp_file in os.listdir(temp_dir):
            try:
                remove(join(temp_dir, temp_file))
            except Exception as e:
                errors.append(f"Error cleaning up temporary file {temp_file}: {str(e)}")
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            errors.append(f"Error removing temporary directory {temp_dir}: {str(e)}")
            
    return new_images_count, new_studies_count, errors
