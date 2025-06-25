from extensions import db

class Studies(db.Model):
    __tablename__ = 'studies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    reviewers = db.relationship('Users', secondary='user_studies', back_populates='studies')
    participants = db.relationship('Participants', back_populates='study')
    images = db.relationship('Images', back_populates='study')

    @property
    def image_count(self):
        return len(self.images)

    @property
    def approved_count(self):
        return sum(1 for img in self.images if img.status == 'approved')

    def __repr__(self):
        return f"<Studies {self.name}>"

# Define the association table for the many-to-many relationship between Users and Studies
user_studies = db.Table('user_studies',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('study_id', db.Integer, db.ForeignKey('studies.id'), primary_key=True)
)
