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
