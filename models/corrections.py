from datetime import datetime
from extensions import db

class Corrections(db.Model):
    __tablename__ = 'corrections'

    id = db.Column(db.Integer, primary_key=True)
    original_text = db.Column(db.Text, nullable=True)
    corrected_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    corrected_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    ocr_result_id = db.Column(db.Integer, db.ForeignKey('ocr_results.id'), nullable=False)

    # Relationships
    user = db.relationship('Users', back_populates='corrections')
    image = db.relationship('Images', back_populates='corrections')
    ocr_result = db.relationship('OCRResults', back_populates='corrections')

    def __repr__(self):
        return f"<Corrections {self.id} status={self.status}>"
