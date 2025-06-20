# tests/integration/test_review_flow.py
import pytest
from models import Study, Participant, Image, User

def test_participant_review_flow(client, db_session):
    # Setup test data
    study = Study(name="Test Study")
    participant = Participant(identifier="P001", study=study)
    user = User(username="reviewer", role="reviewer")
    db_session.add_all([study, participant, user])
    db_session.commit()
    
    # Test empty participant review
    response = client.get(f'/review/study/{study.id}/participant/{participant.id}')
    assert response.status_code == 200
    assert b"No images available" in response.data
    
    # Test with images
    image = Image(filename="test.jpg", participant=participant)
    db_session.add(image)
    db_session.commit()
    
    response = client.get(f'/review/study/{study.id}/participant/{participant.id}')
    assert response.status_code == 200
    assert b"test.jpg" in response.data