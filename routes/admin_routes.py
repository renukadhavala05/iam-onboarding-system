import csv
import hashlib
import io
import os
import pyotp
import datetime
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, make_response
from models.user_model import db, User, Application, AccessRequest
from middleware import admin_required, adaptive_mfa_required
from config import Config
from routes.auth_routes import log_activity

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

    pending_requests = AccessRequest.query.filter_by(status='Pending').count()
    approved_requests = AccessRequest.query.filter_by(status='Approved').all()
    total_assignments = len(approved_requests)
    direct_assignments = sum(1 for req in approved_requests if req.assignment_type == 'AdminDirect')

    expiring_soon = 0
    now = datetime.datetime.now()
    for req in approved_requests:
        if req.expires_at:
            try:
                expiry = datetime.datetime.fromisoformat(req.expires_at)
                if expiry <= now + datetime.timedelta(days=7):
                    expiring_soon += 1
            except ValueError:
                continue

    return render_template("dashboard.html", users=users, active_tab='admin', 
                           total_users=total_users, active_users=active_users, 
                           locked_users=locked_users, admin_users=admin_users,
                           total_logins=total_logins, pending_requests=pending_requests,
                           total_assignments=total_assignments, direct_assignments=direct_assignments,
                           expiring_soon=expiring_soon)

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
            log_activity(f"LEAVER EVENT (Soft Delete): User {username} deactivated by admin {session['user']}")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/onboard_user", methods=["POST"])
@admin_required
def onboard_user():
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
    log_activity(f"ADMIN ACTION: User {username} onboarded by admin {session['user']}")
    flash(f"User {username} successfully onboarded!", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/user/<int:user_id>")
@admin_required
@adaptive_mfa_required
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    # Get audit logs for this user
    user_logs = []
    if os.path.exists(Config.LOG_FILE):
        with open(Config.LOG_FILE, "r") as f:
            user_logs = [line.strip() for line in f.readlines() if user.username in line][-10:]
            user_logs.reverse()
            
    # Get user's approved applications
    approved_reqs = AccessRequest.query.filter_by(user_id=user.id, status='Approved').all()
    user_apps = [req.application for req in approved_reqs]
    
    # Get user's request history
    user_requests = AccessRequest.query.filter_by(user_id=user.id).order_by(AccessRequest.requested_at.desc()).all()
    
    # Get available active applications not currently approved for direct grant
    approved_app_ids = [req.application_id for req in approved_reqs]
    available_apps = Application.query.filter(
        Application.is_active == True,
        ~Application.id.in_(approved_app_ids or [-1])
    ).all()
            
    return render_template(
        "user_profile_admin.html", 
        target_user=user, 
        user_logs=user_logs,
        user_apps=user_apps,
        user_requests=user_requests,
        available_apps=available_apps
    )


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
            log_activity(f"MOVER EVENT: User {user.username} role changed to {new_role} by {session['user']}")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/edit_user", methods=["POST"])
@admin_required
def edit_user():
    user_id = request.form.get("user_id")
    user = User.query.get(user_id)
    if user:
        user.name = request.form.get("name")
        user.email = request.form.get("email")
        user.department = request.form.get("department")
        user.employee_id = request.form.get("employee_id")
        
        db.session.commit()
        flash(f"Identity attributes for {user.username} updated successfully.", "success")
        log_activity(f"MOVER EVENT: User attributes updated for {user.username} by {session['user']}")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/export_users")
@admin_required
@adaptive_mfa_required
def export_users():
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
    
    log_activity(f"AUDIT EXPORT: Identity list exported to CSV by {session['user']}")
    
    return response
