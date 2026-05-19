from flask import Blueprint, render_template, session, redirect, url_for, flash
from models.user_model import db, User
from middleware import admin_required, adaptive_mfa_required
from config import Config
import os

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/dashboard")
@admin_required
@adaptive_mfa_required
def dashboard():
    users = User.query.all()
    total_users = len(users)
    active_users = sum(1 for u in users if (not u.is_locked and u.is_active))
    locked_users = sum(1 for u in users if u.is_locked)
    admin_users = sum(1 for u in users if u.role == 'Admin')
    total_logins = sum((u.login_count or 0) for u in users)
    
    return render_template("dashboard.html", users=users, active_tab='admin', 
                           total_users=total_users, active_users=active_users, 
                           locked_users=locked_users, admin_users=admin_users,
                           total_logins=total_logins)

@admin_bp.route("/logs")
@admin_required
@adaptive_mfa_required
def logs():
    if not os.path.exists(Config.LOG_FILE):
        log_entries = ["No logs found."]
    else:
        with open(Config.LOG_FILE, "r") as f:
            log_entries = f.readlines()
            log_entries.reverse() # Show latest logs first
            
    return render_template("logs.html", logs=log_entries, active_tab='logs')

@admin_bp.route("/toggle_lock/<int:user_id>")
@admin_required
def toggle_lock(user_id):
    user = User.query.get(user_id)
    if user:
        if user.username == session['user']:
            flash("You cannot lock yourself!", "error")
        else:
            user.is_locked = not user.is_locked
            user.failed_attempts = 0 # reset on manual unlock
            db.session.commit()
            flash(f"User {user.username} {'Locked' if user.is_locked else 'Unlocked'}", "success")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/toggle_role/<int:user_id>")
@admin_required
def toggle_role(user_id):
    user = User.query.get(user_id)
    if user:
        if user.username == session['user']:
            flash("You cannot change your own role!", "error")
        else:
            user.role = 'Admin' if user.role == 'User' else 'User'
            db.session.commit()
            flash(f"User {user.username} is now an {user.role}", "success")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        if user.username == session['user']:
            flash("You cannot remove yourself!", "error")
        else:
            username = user.username
            user.is_active = False # JML: Soft Delete (Prevent permanent data loss)
            db.session.commit()
            flash(f"User {username} identity has been deactivated and removed from active roster.", "success")
            # Log the leaver event
            from routes.auth_routes import log_activity
            log_activity(f"LEAVER EVENT (Soft Delete): User {username} deactivated by admin {session['user']}")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/onboard_user", methods=["POST"])
@admin_required
def onboard_user():
    from flask import request
    import hashlib
    import pyotp
    from routes.auth_routes import log_activity

    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")
    phone = request.form.get("phone")
    employee_id = request.form.get("employee_id")
    department = request.form.get("department")
    role = request.form.get("role", "User")
    password = "DefaultPassword123" # Organization default

    if User.query.filter_by(username=username).first():
        flash("Username already exists", "error")
        return redirect(url_for("admin.dashboard"))

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
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

@admin_bp.route("/user/<int:user_id>")
@admin_required
@adaptive_mfa_required
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    # Get audit logs for this user
    from config import Config
    user_logs = []
    if os.path.exists(Config.LOG_FILE):
        with open(Config.LOG_FILE, "r") as f:
            user_logs = [line.strip() for line in f.readlines() if user.username in line][-10:]
            user_logs.reverse()
            
    return render_template("user_profile_admin.html", target_user=user, user_logs=user_logs)

@admin_bp.route("/toggle_active/<int:user_id>")
@admin_required
def toggle_active(user_id):
    user = User.query.get(user_id)
    if user:
        if user.username == session['user']:
            flash("You cannot deactivate yourself!", "error")
        else:
            user.is_active = not user.is_active
            db.session.commit()
            status = "Activated" if user.is_active else "Deactivated"
            flash(f"User {user.username} has been {status}.", "success")
            from routes.auth_routes import log_activity
            log_activity(f"ADMIN ACTION: User {user.username} {status} by {session['user']}")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/update_role", methods=["POST"])
@admin_required
def update_role():
    user_id = request.form.get("user_id")
    new_role = request.form.get("role")
    user = User.query.get(user_id)
    if user:
        if user.username == session['user']:
            flash("You cannot change your own role!", "error")
        else:
            old_role = user.role
            user.role = new_role
            db.session.commit()
            flash(f"User {user.username} role updated from {old_role} to {new_role}.", "success")
            from routes.auth_routes import log_activity
            log_activity(f"MOVER EVENT: User {user.username} role changed to {new_role} by {session['user']}")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/edit_user", methods=["POST"])
@admin_required
def edit_user():
    from flask import request
    user_id = request.form.get("user_id")
    user = User.query.get(user_id)
    if user:
        user.name = request.form.get("name")
        user.email = request.form.get("email")
        user.department = request.form.get("department")
        user.employee_id = request.form.get("employee_id")
        
        db.session.commit()
        flash(f"Identity attributes for {user.username} updated successfully.", "success")
        from routes.auth_routes import log_activity
        log_activity(f"MOVER EVENT: User attributes updated for {user.username} by {session['user']}")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/export_users")
@admin_required
@adaptive_mfa_required
def export_users():
    import csv
    import io
    from flask import make_response
    
    users = User.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow(['ID', 'Username', 'Name', 'Email', 'Role', 'Department', 'EmpID', 'Active', 'Locked'])
    
    for u in users:
        writer.writerow([u.id, u.username, u.name, u.email, u.role, u.department, u.employee_id, u.is_active, u.is_locked])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=iam_users_export.csv"
    response.headers["Content-type"] = "text/csv"
    
    from routes.auth_routes import log_activity
    log_activity(f"AUDIT EXPORT: Identity list exported to CSV by {session['user']}")
    
    return response
