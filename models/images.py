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
    ocr_results = db.relationship('OCRResults', back_populates='image', cascade="all, delete-orphan")
    corrections = db.relationship('Corrections', back_populates='image', cascade="all, delete-orphan")

    @property
    def ocr_status(self):
        """Determine OCR status based on whether OCR results exist"""
        if self.ocr_results:
            return 'processed'
        else:
            return 'unprocessed'
    
    def __repr__(self):
        return f"<Images {self.filename}>"
