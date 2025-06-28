from flask_login import UserMixin
from sqlalchemy import or_ # Пока не используется напрямую, но оставлено
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

from ..extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    owned_sessions = db.relationship(
        'Session',
        backref='owner',
        lazy=True,
        foreign_keys='Session.owner_id',
        cascade="all, delete-orphan"
    )
    collaboration_roles = db.relationship(
        'CollaborationRole',
        backref='user',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Session(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False, default='Новая сессия')
    description = db.Column(db.Text, nullable=True)
    visibility = db.Column(db.String(20), nullable=False, default='private')
    language = db.Column(db.String(50), nullable=False, default="python")
    output = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    timer_started_at = db.Column(db.DateTime, nullable=True)
    timer_duration = db.Column(db.Integer, nullable=True)
    editing_locked = db.Column(db.Boolean, nullable=False, default=False)

    files = db.relationship(
        'File',
        backref='session',
        lazy=True,
        cascade="all, delete-orphan"
    )
    collaborators = db.relationship(
        'CollaborationRole',
        backref='session',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<Session {self.id} (Title: {self.title})>'

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('session.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    language = db.Column(db.String(50), nullable=False)
    is_main = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<File {self.name} in Session {self.session_id}>'

class CollaborationRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='viewer')
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('session_id', 'user_id', name='_session_user_uc'),)

    def __repr__(self):
        return f'<CollaborationRole User:{self.user_id} Session:{self.session_id} Role:{self.role}>'