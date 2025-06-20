from extensions import db

class Participants(db.Model):
    __tablename__ = 'participants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    study_id = db.Column(db.Integer, db.ForeignKey('studies.id'))
    
    study = db.relationship('Studies', back_populates='participants')
    images = db.relationship('Images', back_populates='participant')
    images_dynamic = db.relationship('Images', 
                                   back_populates='participant',
                                   lazy='dynamic',
                                   viewonly=True)
    
    @property
    def image_count(self):
        return len(self.images)
    
    @property
    def approved_count(self):
        return sum(1 for img in self.images if img.status == 'approved')
    
    @property
    def completion_percentage(self):
        if self.image_count > 0:
            return round((self.approved_count / self.image_count) * 100)
        return 0

    def __repr__(self):
        return f'<Participants {self.id}: {self.name}>'
