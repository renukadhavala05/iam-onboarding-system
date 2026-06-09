from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from models.user_model import db, User, Application, AccessRequest
from middleware import admin_required, adaptive_mfa_required
from routes.auth_routes import log_activity
import datetime

app_access_bp = Blueprint("app_access", __name__)

def cleanup_expired_access():
    now = datetime.datetime.now()
    expired_reqs = AccessRequest.query.filter_by(status='Approved').all()
    expired = False
    for req in expired_reqs:
        if req.expires_at:
            try:
                if datetime.datetime.fromisoformat(req.expires_at) <= now:
                    req.status = 'Revoked'
                    req.comments = req.comments or 'Access expired automatically.'
                    req.reviewed_at = str(now)
                    req.reviewed_by = 'System'
                    expired = True
            except ValueError:
                continue
    if expired:
        db.session.commit()

# ==========================================================
# USER APPLICATION ACCESSIBILITY ROUTES
# ==========================================================

@app_access_bp.route("/applications")
def applications():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
        
    cleanup_expired_access()
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    # 1. My Workspace: Active/Approved applications
    approved_reqs = AccessRequest.query.filter_by(user_id=user.id, status='Approved').all()
    my_apps = [req.application for req in approved_reqs if req.application.is_active]

    # 2. Pending Approvals: Currently requested
    pending_reqs = AccessRequest.query.filter_by(user_id=user.id, status='Pending').all()
    pending_app_ids = [req.application_id for req in pending_reqs]

    # 3. Available Catalog: Active apps not yet held or pending, filtered by role visibility
    approved_app_ids = [req.application_id for req in approved_reqs]
    all_active_apps = Application.query.filter_by(is_active=True).all()
    available_apps = [
        app for app in all_active_apps 
        if app.id not in approved_app_ids and app.id not in pending_app_ids and app.is_visible_to_role(user.role)
    ]

    # 4. Access Request History
    history_requests = AccessRequest.query.filter_by(user_id=user.id).order_by(AccessRequest.requested_at.desc()).all()

    return render_template(
        "applications.html", 
        user=user, 
        my_apps=my_apps, 
        pending_requests=pending_reqs, 
        available_apps=available_apps, 
        history_requests=history_requests, 
        active_tab='applications'
    )


@app_access_bp.route("/applications/request", methods=["POST"])
def request_access():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    app_id = request.form.get("app_id")
    reason = request.form.get("reason", "").strip()

    if not app_id:
        flash("Application ID is required.", "error")
        return redirect(url_for('app_access.applications'))

    app = Application.query.get(app_id)
    if not app or not app.is_active or not app.is_visible_to_role(user.role):
        flash("Invalid application selection or access is not permitted for your role.", "error")
        return redirect(url_for('app_access.applications'))

    if not reason:
        flash("Business justification is required to request access.", "error")
        return redirect(url_for('app_access.applications'))

    # Check for existing requests
    existing = AccessRequest.query.filter_by(user_id=user.id, application_id=app.id).first()
    if existing:
        if existing.status in ['Pending', 'Approved']:
            flash(f"You already have a {existing.status} status for {app.name}.", "warning")
            return redirect(url_for('app_access.applications'))
        else:
            # Re-submit previously Rejected/Revoked requests
            existing.status = 'Pending'
            existing.reason = reason
            existing.requested_at = str(datetime.datetime.now())
            existing.comments = None
            existing.reviewed_at = None
            existing.reviewed_by = None
    else:
        # Create a new access request
        new_req = AccessRequest(
            user_id=user.id,
            application_id=app.id,
            status='Pending',
            reason=reason
        )
        db.session.add(new_req)

    db.session.commit()
    log_activity(f"ACCESS REQUEST: User '{user.username}' requested access to app '{app.name}'. Justification: {reason}")
    flash(f"Access request for '{app.name}' has been submitted to the admin approval queue.", "success")
    return redirect(url_for('app_access.applications'))


# ==========================================================
# ADMINISTRATIVE CONTROL ROUTES
# ==========================================================

@app_access_bp.route("/admin/applications")
@admin_required
@adaptive_mfa_required
def admin_apps():
    all_apps = Application.query.all()
    # Annotate apps with count of active users
    app_stats = {}
    for app in all_apps:
        active_users_count = AccessRequest.query.filter_by(application_id=app.id, status='Approved').count()
        app_stats[app.id] = active_users_count
        
    return render_template(
        "admin_applications.html", 
        all_apps=all_apps, 
        app_stats=app_stats,
        active_tab='admin_apps'
    )


@app_access_bp.route("/admin/applications/add", methods=["POST"])
@admin_required
def admin_applications_add():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    url = request.form.get("url", "").strip()
    icon = request.form.get("icon", "").strip() or "🔌"

    if not name or not url:
        flash("Application Name and Redirect URL are required.", "error")
        return redirect(url_for('app_access.admin_apps'))

    existing = Application.query.filter_by(name=name).first()
    if existing:
        flash(f"An application named '{name}' already exists in the catalog.", "error")
        return redirect(url_for('app_access.admin_apps'))

    new_app = Application(
        name=name,
        description=description,
        category=category,
        url=url,
        icon=icon,
        allowed_roles=','.join(sorted({r.strip() for r in (request.form.get('allowed_roles', 'User,Admin') or '').split(',') if r.strip()})) or 'User,Admin'
    )
    db.session.add(new_app)
    db.session.commit()

    log_activity(f"ADMIN ACTION: App '{name}' added to catalog by admin '{session['user']}'")
    flash(f"Application '{name}' successfully added to catalog.", "success")
    return redirect(url_for('app_access.admin_apps'))


@app_access_bp.route("/admin/applications/edit", methods=["POST"])
@admin_required
def admin_applications_edit():
    app_id = request.form.get("app_id")
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    url = request.form.get("url", "").strip()
    icon = request.form.get("icon", "").strip() or "🔌"

    if not app_id or not name or not url:
        flash("Missing parameters for application update.", "error")
        return redirect(url_for('app_access.admin_apps'))

    app = Application.query.get(app_id)
    if not app:
        flash("Application not found.", "error")
        return redirect(url_for('app_access.admin_apps'))

    old_name = app.name
    app.name = name
    app.description = description
    app.category = category
    app.url = url
    app.icon = icon
    app.allowed_roles = ','.join(sorted({r.strip() for r in (request.form.get('allowed_roles', app.allowed_roles or 'User,Admin') or '').split(',') if r.strip()})) or 'User,Admin'

    db.session.commit()
    log_activity(f"ADMIN ACTION: App '{old_name}' updated (New Name: '{name}') by admin '{session['user']}'")
    flash(f"Application '{name}' details updated successfully.", "success")
    return redirect(url_for('app_access.admin_apps'))


@app_access_bp.route("/admin/applications/toggle/<int:app_id>", methods=["POST"])
@admin_required
def admin_applications_toggle(app_id):
    app = Application.query.get_or_404(app_id)
    app.is_active = not app.is_active
    db.session.commit()

    status_str = "Activated" if app.is_active else "Deactivated"
    log_activity(f"ADMIN ACTION: App '{app.name}' has been {status_str.lower()} by admin '{session['user']}'")
    flash(f"Application '{app.name}' has been {status_str}.", "success")
    return redirect(url_for('app_access.admin_apps'))


@app_access_bp.route("/admin/requests")
@admin_required
@adaptive_mfa_required
def admin_requests():
    pending_reqs = AccessRequest.query.filter_by(status='Pending').order_by(AccessRequest.requested_at.desc()).all()
    return render_template(
        "admin_requests.html", 
        pending_requests=pending_reqs, 
        active_tab='admin_requests'
    )


@app_access_bp.route("/admin/request/approve/<int:request_id>", methods=["POST"])
@admin_required
def admin_request_approve(request_id):
    req = AccessRequest.query.get_or_404(request_id)
    comments = request.form.get("comments", "Approved by Administrator.").strip() or "Approved by Administrator."

    req.status = 'Approved'
    req.reviewed_at = str(datetime.datetime.now())
    req.reviewed_by = session['user']
    req.comments = comments
    req.expires_at = str(datetime.datetime.now() + datetime.timedelta(days=30))
    req.assignment_type = 'Request'
    db.session.commit()

    log_activity(f"ACCESS APPROVED: Application '{req.application.name}' granted for user '{req.user.username}' by admin '{session['user']}'")
    flash(f"Access request from '{req.user.username}' for '{req.application.name}' approved.", "success")
    return redirect(url_for('app_access.admin_requests'))


@app_access_bp.route("/admin/request/reject/<int:request_id>", methods=["POST"])
@admin_required
def admin_request_reject(request_id):
    req = AccessRequest.query.get_or_404(request_id)
    comments = request.form.get("comments", "").strip()

    if not comments:
        flash("Rejection comments are required to deny access.", "error")
        return redirect(url_for('app_access.admin_requests'))

    req.status = 'Rejected'
    req.reviewed_at = str(datetime.datetime.now())
    req.reviewed_by = session['user']
    req.comments = comments
    db.session.commit()

    log_activity(f"ACCESS REJECTED: Application '{req.application.name}' denied for user '{req.user.username}' by admin '{session['user']}'. Reason: {comments}")
    flash(f"Access request from '{req.user.username}' for '{req.application.name}' rejected.", "success")
    return redirect(url_for('app_access.admin_requests'))


@app_access_bp.route("/admin/request/revoke/<int:user_id>/<int:app_id>", methods=["POST"])
@admin_required
def admin_request_revoke(user_id, app_id):
    req = AccessRequest.query.filter_by(user_id=user_id, application_id=app_id, status='Approved').first()
    if not req:
        flash("No active access authorization record found.", "error")
        return redirect(url_for('admin.view_user', user_id=user_id))

    comments = request.form.get("comments", "Access authorization revoked by Admin.").strip() or "Access authorization revoked by Admin."
    req.status = 'Revoked'
    req.reviewed_at = str(datetime.datetime.now())
    req.reviewed_by = session['user']
    req.comments = comments
    db.session.commit()

    log_activity(f"ACCESS REVOKED: Access to '{req.application.name}' revoked for user '{req.user.username}' by admin '{session['user']}'")
    flash(f"Access to '{req.application.name}' has been successfully revoked.", "success")
    return redirect(url_for('admin.view_user', user_id=user_id))


@app_access_bp.route("/admin/request/grant/<int:user_id>", methods=["POST"])
@admin_required
def admin_request_grant(user_id):
    app_id = request.form.get("app_id")
    if not app_id:
        flash("Select an application to grant access.", "error")
        return redirect(url_for('admin.view_user', user_id=user_id))

    user = User.query.get_or_404(user_id)
    app = Application.query.get_or_404(app_id)

    # Check existing request
    existing = AccessRequest.query.filter_by(user_id=user.id, application_id=app.id).first()
    if existing:
        if existing.status == 'Approved':
            flash(f"User '{user.username}' already holds active access permission for '{app.name}'.", "warning")
            return redirect(url_for('admin.view_user', user_id=user_id))
        else:
            # Upgrade existing status to Approved
            existing.status = 'Approved'
            existing.reason = "Assigned directly by administrator."
            existing.reviewed_at = str(datetime.datetime.now())
            existing.reviewed_by = session['user']
            existing.comments = "Assigned directly by administrator."
            existing.expires_at = str(datetime.datetime.now() + datetime.timedelta(days=30))
            existing.assignment_type = 'AdminDirect'
            db.session.commit()
            log_activity(f"ACCESS GRANTED: Application '{app.name}' granted for user '{user.username}' by admin '{session['user']}'")
            flash(f"Access to '{app.name}' has been granted to '{user.username}'.", "success")
            return redirect(url_for('admin.view_user', user_id=user_id))
    else:
        # Create directly approved record
        req = AccessRequest(
            user_id=user.id,
            application_id=app.id,
            status='Approved',
            reason="Assigned directly by administrator.",
            reviewed_at=str(datetime.datetime.now()),
            reviewed_by=session['user'],
            comments="Assigned directly by administrator.",
            expires_at=str(datetime.datetime.now() + datetime.timedelta(days=30)),
            assignment_type='AdminDirect'
        )
        db.session.add(req)
        db.session.commit()
        log_activity(f"ACCESS GRANTED: Application '{app.name}' granted for user '{user.username}' by admin '{session['user']}'")
        flash(f"Access to '{app.name}' has been granted to '{user.username}'.", "success")
        return redirect(url_for('admin.view_user', user_id=user_id))
