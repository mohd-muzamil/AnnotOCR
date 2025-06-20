from datetime import datetime
from extensions import db
from flask_login import UserMixin

class Users(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='reviewer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    corrections = db.relationship('Corrections', back_populates='user')

    def __repr__(self):
        return f"<Users {self.username}>"
