from extensions import db

class Images(db.Model):
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pending')
    upload_time = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    study_id = db.Column(db.Integer, db.ForeignKey('studies.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)

    study = db.relationship('Studies', back_populates='images')
    participant = db.relationship('Participants', back_populates='images')
    ocr_results = db.relationship('OCRResults', back_populates='image')
    corrections = db.relationship('Corrections', back_populates='image')

    def __repr__(self):
        return f"<Images {self.filename}>"
