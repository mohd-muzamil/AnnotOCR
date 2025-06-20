# services/data_loader.py
# This script is responsible for loading image data from a static directory structure into the application's database.
# It iterates through directories representing studies and participants, creating corresponding database entries if they do not exist.
# For each image file found, it checks if the image is already in the database before adding it with a 'pending' status.
# This service is crucial for initializing or updating the database with image data for further processing like OCR.

import os
from extensions import db
from models import Studies, Participants, Images

def load_images_from_static():
    image_root = os.path.join('static', 'images')
    
    for study_name in os.listdir(image_root):
        study_path = os.path.join(image_root, study_name)
        if not os.path.isdir(study_path):
            continue

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
                continue

        # Process each participant
        for participant_id in os.listdir(study_path):
            participant_path = os.path.join(study_path, participant_id)
            if not os.path.isdir(participant_path):
                continue

            try:
                participant = Participants.query.filter_by(
                    name=participant_id, 
                    study_id=study.id
                ).first()
                
                if not participant:
                    participant = Participants(
                        name=participant_id, 
                        study_id=study.id
                    )
                    db.session.add(participant)
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error processing participant {participant_id}: {e}")
                continue

            # Process each image
            for filename in os.listdir(participant_path):
                if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue

                relative_path = os.path.join('images', study_name, participant_id, filename)
                
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
                    print(f"Error processing image {filename}: {e}")
                    continue

    print("Finished loading images into database")
