from flask import Blueprint, render_template, session, redirect, url_for
from models.user_model import User
import os
from config import Config

user_bp = Blueprint("user", __name__)

@user_bp.route("/")
def index():
    if 'user' in session:
        return redirect(url_for('user.dashboard'))
    return redirect(url_for('auth.register'))

@user_bp.route("/dashboard")
def dashboard():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    current_user = User.query.filter_by(username=session['user']).first()
    
    # Parse activity feed
    recent_activity = []
    if os.path.exists(Config.LOG_FILE):
        with open(Config.LOG_FILE, "r") as f:
            lines = f.readlines()
            user_logs = [line.strip() for line in lines if session['user'] in line]
            recent_activity = list(reversed(user_logs[-5:]))
            
    total_users = User.query.count()
    admin_users = User.query.filter_by(role='Admin').count()
            
    return render_template("dashboard.html", user=current_user, active_tab='profile', 
                           recent_activity=recent_activity, total_users=total_users, admin_users=admin_users)