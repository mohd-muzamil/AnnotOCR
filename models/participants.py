from extensions import db

class Participants(db.Model):
    __tablename__ = 'participants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    study_id = db.Column(db.Integer, db.ForeignKey('studies.id'), nullable=False)

    study = db.relationship('Studies', back_populates='participants')
    images = db.relationship('Images', back_populates='participant')

    def __repr__(self):
        return f"<Participants {self.name}>"
