from datetime import datetime
from extensions import db

class Images(db.Model):
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    ocr_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    
    # Foreign keys
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    study_id = db.Column(db.Integer, db.ForeignKey('studies.id'), nullable=False)
    
    # Relationships
    participant = db.relationship('Participants', back_populates='images')
    study = db.relationship('Studies', back_populates='images')
    corrections = db.relationship('Corrections', back_populates='image')
    ocr_results = db.relationship('OCRResults', back_populates='image', uselist=False)

    def __repr__(self):
        return f"<Images {self.filename} (status: {self.status})>"
    
    @property
    def ocr_text_content(self):
        """Safe access to OCR text content"""
        if self.ocr_results:
            return self.ocr_results[0].text
        return None
