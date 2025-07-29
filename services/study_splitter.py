from app import db
from models import Studies, Images

def split_study_into_batches(study_id, batch_size):
    """
    Split a study into batch studies by moving participants (and their images) to new studies.
    This approach moves the actual data so that batch studies are independent but derived from the original.
    """
    try:
        from models import Participants
        
        original_study = Studies.query.get_or_404(study_id)
        participants = Participants.query.filter_by(study_id=study_id).all()
        
        if not participants:
            raise Exception("No participants to split.")

        # Group participants into batches
        participant_chunks = [participants[i:i + batch_size] for i in range(0, len(participants), batch_size)]
        created_studies = []

        for i, chunk in enumerate(participant_chunks):
            batch_number = i + 1
            new_study_name = f"{original_study.name}_batch_{batch_number}"
            
            existing_study = Studies.query.filter_by(name=new_study_name).first()
            if existing_study:
                print(f"Study '{new_study_name}' already exists. Skipping.")
                continue

            # Create new batch study
            new_study = Studies(name=new_study_name, description=f"Batch {batch_number} of {original_study.name}")
            db.session.add(new_study)
            db.session.flush()  # To get the new_study.id

            # Move participants to the new batch study
            for participant in chunk:
                # Update the participant to belong to the new study
                participant.study_id = new_study.id
                
                # Update all images of this participant to belong to the new study
                participant_images = Images.query.filter_by(participant_id=participant.id).all()
                for image in participant_images:
                    image.study_id = new_study.id
            
            created_studies.append(new_study_name)

        db.session.commit()
        return created_studies
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Failed to split study: {str(e)}")


def merge_batch_studies_back(original_study_id):
    """
    Merge all batch studies back to the original study.
    This moves participants and images from batch studies back to the original study.
    """
    try:
        from models import Participants
        
        original_study = Studies.query.get_or_404(original_study_id)
        original_study_name = original_study.name
        
        # Find all batch studies for this original study
        batch_studies = Studies.query.filter(
            Studies.name.like(f"{original_study_name}_batch_%")
        ).all()
        
        if not batch_studies:
            raise Exception("No batch studies found to merge.")
        
        merged_count = 0
        for batch_study in batch_studies:
            # Move all participants from batch study back to original study
            batch_participants = Participants.query.filter_by(study_id=batch_study.id).all()
            
            for participant in batch_participants:
                # Update participant to belong to original study
                participant.study_id = original_study.id
                
                # Update all images of this participant to belong to original study
                participant_images = Images.query.filter_by(participant_id=participant.id).all()
                for image in participant_images:
                    image.study_id = original_study.id
                
                merged_count += 1
        
        db.session.commit()
        return merged_count, len(batch_studies)
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Failed to merge batch studies: {str(e)}")


def delete_batch_studies(original_study_id):
    """
    Delete all empty batch studies for the given original study.
    This should only be called after merging batch studies back to the original.
    """
    try:
        from models import Participants
        
        original_study = Studies.query.get_or_404(original_study_id)
        original_study_name = original_study.name
        
        # Find all batch studies for this original study
        batch_studies = Studies.query.filter(
            Studies.name.like(f"{original_study_name}_batch_%")
        ).all()
        
        if not batch_studies:
            raise Exception("No batch studies found to delete.")
        
        deleted_studies = []
        for batch_study in batch_studies:
            # Check if batch study is empty (no participants/images)
            participant_count = Participants.query.filter_by(study_id=batch_study.id).count()
            image_count = Images.query.filter_by(study_id=batch_study.id).count()
            
            if participant_count == 0 and image_count == 0:
                deleted_studies.append(batch_study.name)
                db.session.delete(batch_study)
            else:
                raise Exception(f"Batch study '{batch_study.name}' is not empty. Merge first before deleting.")
        
        db.session.commit()
        return deleted_studies
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Failed to delete batch studies: {str(e)}")
