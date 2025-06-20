from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from extensions import db
from models.participants import Participants
from models.images import Images

class Studies(db.Model):
    __tablename__ = 'studies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    participants = db.relationship('Participants', back_populates='study')
    participants_dynamic = db.relationship('Participants', 
                                         back_populates='study',
                                         lazy='dynamic',
                                         viewonly=True)
    images = db.relationship('Images', back_populates='study')

    @hybrid_property
    def image_count(self):
        return db.session.query(Images)\
            .join(Participants)\
            .filter(Participants.study_id == self.id)\
            .count()
    
    @hybrid_property
    def approved_count(self):
        return db.session.query(Images)\
            .join(Participants)\
            .filter(
                Participants.study_id == self.id,
                Images.status == 'approved'
            )\
            .count()
    
    @hybrid_property
    def completion_percentage(self):
        if self.image_count > 0:
            return round((self.approved_count / self.image_count) * 100)
        return 0

    def __repr__(self):
        return f'<Studies {self.id}: {self.name}>'
