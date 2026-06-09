from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    employee_id = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(50))
    role = db.Column(db.String(20), default='User') # 'User' or 'Admin'
    
    # Security fields
    otp_secret = db.Column(db.String(32)) # For TOTP
    is_locked = db.Column(db.Boolean, default=False) # Security lock
    is_active = db.Column(db.Boolean, default=True)  # Administrative status
    failed_attempts = db.Column(db.Integer, default=0)
    
    # Tracking fields
    last_login_ip = db.Column(db.String(45))
    last_login_at = db.Column(db.String(100))
    login_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.String(100), default=lambda: str(datetime.datetime.now()))

    def __repr__(self):
        return f'<User {self.username}>'


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    category = db.Column(db.String(50)) # e.g. Cloud Services, Collaboration, Developer Tools
    url = db.Column(db.String(255))
    icon = db.Column(db.String(50)) # emoji or icon name
    is_active = db.Column(db.Boolean, default=True)
    allowed_roles = db.Column(db.String(255), default='User,Admin')

    def is_visible_to_role(self, role):
        if not self.allowed_roles:
            return True
        roles = [r.strip() for r in self.allowed_roles.split(',') if r.strip()]
        return role in roles

    def normalized_allowed_roles(self):
        return ','.join(sorted({r.strip() for r in (self.allowed_roles or '').split(',') if r.strip()}))

    def __repr__(self):
        return f'<Application {self.name}>'


class AccessRequest(db.Model):
    __tablename__ = 'access_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending') # 'Pending', 'Approved', 'Rejected', 'Revoked'
    reason = db.Column(db.String(255))
    comments = db.Column(db.String(255))
    requested_at = db.Column(db.String(100), default=lambda: str(datetime.datetime.now()))
    reviewed_at = db.Column(db.String(100))
    reviewed_by = db.Column(db.String(100)) # Admin username
    expires_at = db.Column(db.String(100))
    assignment_type = db.Column(db.String(40), default='Request') # 'Request' or 'AdminDirect'

    user = db.relationship('User', backref=db.backref('access_requests', lazy=True, cascade="all, delete-orphan"))
    application = db.relationship('Application', backref=db.backref('access_requests', lazy=True, cascade="all, delete-orphan"))

    def is_expired(self):
        if not self.expires_at:
            return False
        try:
            return datetime.datetime.fromisoformat(self.expires_at) <= datetime.datetime.now()
        except ValueError:
            return False

    def __repr__(self):
        return f'<AccessRequest User:{self.user_id} App:{self.application_id} Status:{self.status}>'

