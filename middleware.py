import datetime
import logging
from functools import wraps
from flask import request, jsonify, session, flash, url_for, redirect
from models.user_model import User

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ip_logic_middleware(app):
    @app.before_request
    def check_security():
        # Exclude static files and health checks
        if request.path.startswith('/static') or request.path.startswith('/logout'):
            return

        # Continuous Verification (Zero Trust Principle)
        if 'user' in session:
            # 1. IP Binding Validation
            current_ip = request.remote_addr
            stored_ip = session.get('ip')
            
            if stored_ip and current_ip != stored_ip:
                logger.warning(f"ADAPTIVE AUTH: IP Change detected for {session['user']}: {stored_ip} -> {current_ip}")
                session['next_url'] = request.path
                session.pop('mfa_verified_at', None) # Force re-verification
                flash("Zero Trust Alert: Your network environment has changed. Please re-verify your identity to continue.", "warning")
                return redirect(url_for('auth.mfa_verify'))

            # 2. Continuous Role Verification (Mover Check)
            # Ensure the session role matches the database in real-time
            user = User.query.filter_by(username=session['user']).first()
            if not user or user.is_locked:
                logger.warning(f"SECURITY ALERT: Revoked user {session.get('user')} attempted access.")
                session.clear()
                return jsonify({"error": "Access Revoked: Account locked or removed."}), 403
            
            if session.get('role') != user.role:
                logger.info(f"Role change detected for {user.username}. Updating session.")
                session['role'] = user.role
                # If they were demoted, we might want to redirect them or restrict current request
                if user.role != 'Admin' and request.path.startswith('/admin'):
                     return jsonify({"error": "Least Privilege Violation: Unauthorized access."}), 403

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        
        # Double check role in session (Continuous check)
        if session.get('role') != 'Admin':
            logger.warning(f"Unauthorized admin access attempt by {session.get('user')}")
            return jsonify({"error": "Access denied: Admin role required"}), 403
            
        return f(*args, **kwargs)
    return decorated_function

def adaptive_mfa_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
            
        # Check if MFA was verified recently (within the last 10 minutes)
        # (Zero Trust: Adaptive Verification for sensitive areas)
        mfa_at = session.get('mfa_verified_at')
        now = datetime.datetime.now().timestamp()
        
        if not mfa_at or (now - mfa_at) > 600: # 10 minutes session TTL for sensitive actions
            logger.info(f"Identity Verification expired for {session['user']}. Adaptive MFA triggered.")
            session['next_url'] = request.path # Save for redirection after re-auth
            flash("Adaptive Authentication: Please re-verify your identity to access sensitive controls.", "warning")
            return redirect(url_for('auth.mfa_verify'))
            
        return f(*args, **kwargs)
    return decorated_function

def security_headers(app):
    @app.after_request
    def add_security_headers(response):
        # Adding stricter Zero Trust headers
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:;"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
