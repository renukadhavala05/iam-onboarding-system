import os
from flask import Flask, session
from sqlalchemy import text
from config import Config
from models.user_model import db, User
from middleware import ip_logic_middleware, security_headers
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.user_routes import user_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    # Initialize DB
    db.init_app(app)

    # Initialize Middleware
    ip_logic_middleware(app)
    security_headers(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp)
    
    from routes.app_routes import app_access_bp
    app.register_blueprint(app_access_bp)

    @app.context_processor
    def inject_pending_requests():
        if 'role' in session and session['role'] == 'Admin':
            try:
                from models.user_model import AccessRequest
                count = AccessRequest.query.filter_by(status='Pending').count()
                return dict(pending_requests_count=count)
            except Exception:
                return dict(pending_requests_count=0)
        return dict(pending_requests_count=0)

    def seed_default_applications():
        from models.user_model import Application
        try:
            if Application.query.count() == 0:
                default_apps = [
                    Application(name="AWS Console", description="Amazon Web Services cloud infrastructure control plane.", category="Cloud Services", url="https://aws.amazon.com/console", icon="☁️", allowed_roles="Admin,User"),
                    Application(name="Slack", description="Team communication, instant messaging, and channels platform.", category="Collaboration", url="https://slack.com", icon="💬", allowed_roles="Admin,User"),
                    Application(name="GitHub", description="Code repository management, version control, and pull requests.", category="Developer Tools", url="https://github.com", icon="💻", allowed_roles="Admin,User"),
                    Application(name="Jira", description="Project tracking, issue management, and agile software development boards.", category="Project Management", url="https://jira.atlassian.com", icon="📊", allowed_roles="Admin,User"),
                    Application(name="Salesforce", description="Customer Relationship Management (CRM) dashboard for sales and client success.", category="Sales & CRM", url="https://salesforce.com", icon="📈", allowed_roles="Admin,User"),
                    Application(name="Office 365", description="Corporate productivity suite including email, documents, and cloud storage.", category="Productivity", url="https://office.com", icon="📂", allowed_roles="Admin,User")
                ]
                db.session.bulk_save_objects(default_apps)
                db.session.commit()
                print("Seeded default applications successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding default applications: {e}")

    # CLI Commands
    @app.cli.command("init-db")
    def init_db():
        """Clear the existing data and create new tables."""
        db.drop_all()
        db.create_all()
        seed_default_applications()
        print("Initialized the database.")

    @app.cli.command("reset-logs")
    def reset_logs():
        """Clear the log file."""
        if os.path.exists(Config.LOG_FILE):
            with open(Config.LOG_FILE, "w") as f:
                f.truncate(0)
            print("Logs cleared.")
        else:
            print("No log file found to clear.")

    def migrate_database_schema():
        try:
            with db.engine.begin() as conn:
                result = conn.execute(text("PRAGMA table_info(applications)"))
                app_columns = [row[1] for row in result.fetchall()]
                if 'allowed_roles' not in app_columns:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN allowed_roles VARCHAR(255) DEFAULT 'Admin,User'"))

                result = conn.execute(text("PRAGMA table_info(access_requests)"))
                req_columns = [row[1] for row in result.fetchall()]
                if 'expires_at' not in req_columns:
                    conn.execute(text("ALTER TABLE access_requests ADD COLUMN expires_at VARCHAR(100)"))
                if 'assignment_type' not in req_columns:
                    conn.execute(text("ALTER TABLE access_requests ADD COLUMN assignment_type VARCHAR(40) DEFAULT 'Request'"))
        except Exception:
            pass

    with app.app_context():
        db.create_all()
        migrate_database_schema()
        seed_default_applications()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)