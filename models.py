from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin' or 'user'
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class SharedAccessRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'approved', 'rejected'

    user = db.relationship('User', backref=db.backref('shared_requests', lazy=True))


class FilePermission(db.Model):
    """
    Stores ownership and access permissions for files uploaded to shared/.
    Files inside users/<username>/ are implicitly private — no DB record needed.

    visibility:
        'private'  → only owner + admin can access (even within shared/)
        'shared'   → all approved users can read; write/delete controlled by flags

    Defaults for shared uploads:
        can_read   = True   (visible to all approved users)
        can_write  = True   (owner can rename/overwrite)
        can_delete = False  (only owner + admin can delete)
    """
    __tablename__ = 'file_permission'

    id         = db.Column(db.Integer, primary_key=True)
    rel_path   = db.Column(db.String(512), unique=True, nullable=False)  # path relative to NAS_ROOT
    owner_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    visibility = db.Column(db.String(20), default='shared', nullable=False)  # 'private' | 'shared'
    can_read   = db.Column(db.Boolean, default=True, nullable=False)
    can_write  = db.Column(db.Boolean, default=True, nullable=False)
    can_delete = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    owner = db.relationship('User', backref=db.backref('owned_files', lazy='dynamic'))

    def __repr__(self):
        return f'<FilePermission {self.rel_path} owner={self.owner_id}>'
