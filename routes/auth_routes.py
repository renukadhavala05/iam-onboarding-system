from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from models.user_model import db, User
import hashlib
import pyotp
import datetime
import qrcode
import io
import base64
from config import Config

auth_bp = Blueprint("auth", __name__)

def log_activity(message):
    with open(Config.LOG_FILE, "a") as f:
        f.write(f"{datetime.datetime.now()} - {message}\n")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("index.html")

    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")
    phone = request.form.get("phone")
    employee_id = request.form.get("employee_id")
    department = request.form.get("department")
    password = request.form.get("password")

    if User.query.filter_by(username=username).first():
        flash("Username already taken", "error")
        return redirect(url_for("auth.register"))

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    # First user becomes Admin
    is_first_user = User.query.count() == 0
    role = 'Admin' if is_first_user else 'User'

    # Use standard 32-character secret (160 bits) for maximum compatibility 
    # (Google Authenticator strictly requires longer keys)
    otp_secret = pyotp.random_base32()

    user = User(
        username=username,
        password=hashed_password,
        name=name,
        email=email,
        phone=phone,
        employee_id=employee_id,
        department=department,
        role=role,
        otp_secret=otp_secret
    )

    db.session.add(user)
    db.session.commit()

    flash(f"User created successfully as {role}! Please login.", "success")
    log_activity(f"User registered: {username} ({role})")
    return redirect(url_for("auth.login"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter_by(username=username).first()

    if not user:
        flash("User not found", "error")
        return redirect(url_for("auth.login"))

    if user.is_locked:
        flash("Account is locked due to high risk / suspicious activity.", "error")
        return redirect(url_for("auth.login"))

    hashed_input = hashlib.sha256(password.encode()).hexdigest()

    if hashed_input == user.password:
        # Password correct, now verify MFA
        session['temp_user'] = username
        return redirect(url_for("auth.mfa_verify"))
    else:
        user.failed_attempts += 1
        if user.failed_attempts >= 3:
            user.is_locked = True
            log_activity(f"SECURITY ALERT: Account locked for {username} due to failed attempts")
        
        db.session.commit()
        flash(f"Invalid credentials. Attempts: {user.failed_attempts}", "error")
        return redirect(url_for("auth.login"))

@auth_bp.route("/mfa-verify", methods=["GET", "POST"])
def mfa_verify():
    if 'temp_user' not in session and 'user' not in session:
        return redirect(url_for("auth.login"))
    
    username = session.get('temp_user') or session.get('user')
    user = User.query.filter_by(username=username).first()

    if request.method == "POST":
        token = request.form.get("otp")
        totp = pyotp.TOTP(user.otp_secret, digits=6)
        
        if totp.verify(token):
            # Success: Establish or Refresh Secure Session
            verified_at = datetime.datetime.now().timestamp()
            
            # If it's a re-auth (Adaptive MFA)
            if 'user' in session:
                session['mfa_verified_at'] = verified_at
                log_activity(f"Adaptive Identity Re-verified: {session['user']}")
                next_url = session.get('next_url', url_for("user.dashboard"))
                session.pop('next_url', None)
                return redirect(next_url)
            
            # First time Login
            session.clear()
            session['user'] = user.username
            session['role'] = user.role
            session['ip'] = request.remote_addr
            session['mfa_verified_at'] = verified_at
            
            user.failed_attempts = 0
            user.last_login_ip = request.remote_addr
            user.last_login_at = str(datetime.datetime.now())
            if user.login_count is None:
                user.login_count = 0
            user.login_count += 1
            db.session.commit()
            
            log_activity(f"Successful Zero Trust Login: {username} from {request.remote_addr}")
            return redirect(url_for("user.dashboard"))
        else:
            flash("Invalid OTP code", "error")
            return redirect(url_for("auth.mfa_verify"))

    # Generate QR Code for easy setup
    otp_uri = pyotp.totp.TOTP(user.otp_secret).provisioning_uri(
        name=user.username, 
        issuer_name="ZeroTrustIAM"
    )
    # Auto-adjusting QR Code size
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(otp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    return render_template("mfa_verify.html", otp_secret=user.otp_secret, qr_code=qr_base64)

@auth_bp.route("/logout")
def logout():
    log_activity(f"Logout: {session.get('user')}")
    session.clear()
    return redirect(url_for("auth.login"))

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")
    
    username = request.form.get("username")
    employee_id = request.form.get("employee_id")
    
    user = User.query.filter_by(username=username, employee_id=employee_id).first()
    
    if user:
        session['reset_user'] = username
        log_activity(f"Password reset initiated for: {username}")
        return redirect(url_for('auth.reset_password'))
    else:
        # Prevent username enumeration securely
        flash("If your attributes matched, you'll be moved to the reset screen. Please check your data.", "error")
        return redirect(url_for('auth.forgot_password'))

@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if 'reset_user' not in session:
        return redirect(url_for('auth.login'))
        
    if request.method == "GET":
        return render_template("reset_password.html")
        
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")
    
    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for('auth.reset_password'))
        
    username = session['reset_user']
    user = User.query.filter_by(username=username).first()
    
    if user:
        user.password = hashlib.sha256(new_password.encode()).hexdigest()
        db.session.commit()
        log_activity(f"Password updated securely for: {username}")
        flash("Password successfully reset! You can now log in.", "success")
        
    session.pop('reset_user', None)
    return redirect(url_for('auth.login'))