from extensions import db
from datetime import datetime

class Corrections(db.Model):
    __tablename__ = 'corrections'

    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ocr_result_id = db.Column(db.Integer, db.ForeignKey('ocr_results.id'), nullable=True)
    original_text = db.Column(db.Text, nullable=True)
    corrected_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    image = db.relationship('Images', back_populates='corrections')
    user = db.relationship('Users', back_populates='corrections')
    ocr_result = db.relationship('OCRResults', back_populates='corrections')

    def __repr__(self):
        return f"<Corrections {self.id} for Image {self.image_id}>"
