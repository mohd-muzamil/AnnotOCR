from datetime import datetime
from extensions import db

class OCRResults(db.Model):
    __tablename__ = 'ocr_results'
    
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Float)
    language = db.Column(db.String(10), default='eng')
    version = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    image = db.relationship('Images', back_populates='ocr_results')
    corrections = db.relationship('Corrections', back_populates='ocr_result')

    def __repr__(self):
        return f"<OCRResults {self.id} image_id={self.image_id}>"
