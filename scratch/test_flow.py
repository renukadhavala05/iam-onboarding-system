import sys
import os

# Append the project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.user_model import db, User, Application, AccessRequest

def test_workflow():
    app = create_app()
    with app.app_context():
        print("--- VERIFICATION FLOW STARTED ---")
        
        # 1. Clean and initialize database
        db.drop_all()
        db.create_all()
        
        # Seed default applications since we dropped the database tables
        default_apps = [
            Application(name="AWS Console", description="Amazon Web Services cloud infrastructure control plane.", category="Cloud Services", url="https://aws.amazon.com/console", icon="☁️"),
            Application(name="Slack", description="Team communication, instant messaging, and channels platform.", category="Collaboration", url="https://slack.com", icon="💬"),
            Application(name="GitHub", description="Code repository management, version control, and pull requests.", category="Developer Tools", url="https://github.com", icon="💻"),
            Application(name="Jira", description="Project tracking, issue management, and agile software development boards.", category="Project Management", url="https://jira.atlassian.com", icon="📊"),
            Application(name="Salesforce", description="Customer Relationship Management (CRM) dashboard for sales and client success.", category="Sales & CRM", url="https://salesforce.com", icon="📈"),
            Application(name="Office 365", description="Corporate productivity suite including email, documents, and cloud storage.", category="Productivity", url="https://office.com", icon="📂")
        ]
        db.session.bulk_save_objects(default_apps)
        db.session.commit()
        
        app.extensions['migrate'] = None # Suppress migrations warnings if any
        
        # Verify seeding occurred
        apps = Application.query.all()
        print(f"Seeded applications count: {len(apps)}")
        for app_obj in apps:
            print(f"  - [{app_obj.category}] {app_obj.name}: {app_obj.url}")
        
        assert len(apps) == 6, "Seeding failed: expected 6 applications."
        
        # 2. Create test users
        admin_user = User(
            username="admin_test",
            password="hashed_admin_password",
            name="Admin Tester",
            email="admin@test.org",
            phone="1234567890",
            employee_id="EMP-0001",
            department="IT Security",
            role="Admin"
        )
        regular_user = User(
            username="user_test",
            password="hashed_user_password",
            name="Regular Tester",
            email="user@test.org",
            phone="0987654321",
            employee_id="EMP-0002",
            department="Engineering",
            role="User"
        )
        
        db.session.add(admin_user)
        db.session.add(regular_user)
        db.session.commit()
        print("\nCreated Admin User: 'admin_test' and Regular User: 'user_test'")
        
        # 3. Create an Access Request (e.g. for Slack)
        slack_app = Application.query.filter_by(name="Slack").first()
        assert slack_app is not None, "Slack application not found in seeded data."
        
        req = AccessRequest(
            user_id=regular_user.id,
            application_id=slack_app.id,
            status='Pending',
            reason="I need Slack for daily standups and engineering updates."
        )
        db.session.add(req)
        db.session.commit()
        print(f"\nUser '{regular_user.username}' requested access to '{slack_app.name}' (Reason: '{req.reason}')")
        
        # Verify request exists and is Pending
        req_check = AccessRequest.query.filter_by(user_id=regular_user.id, application_id=slack_app.id).first()
        assert req_check is not None
        assert req_check.status == 'Pending'
        print(f"Verified: Request status is '{req_check.status}'")
        
        # 4. Admin Approves the Request
        req_check.status = 'Approved'
        req_check.reviewed_by = admin_user.username
        req_check.reviewed_at = "2026-06-08 12:00:00"
        req_check.comments = "Approved for engineering team communications."
        db.session.commit()
        print(f"\nAdmin '{admin_user.username}' approved request with comments: '{req_check.comments}'")
        
        # Verify approved request
        req_approved = AccessRequest.query.filter_by(user_id=regular_user.id, application_id=slack_app.id).first()
        assert req_approved.status == 'Approved'
        print(f"Verified: Access is now '{req_approved.status}'")
        
        # Check active user applications helper list
        user_approved_reqs = AccessRequest.query.filter_by(user_id=regular_user.id, status='Approved').all()
        user_apps = [r.application for r in user_approved_reqs]
        print(f"User '{regular_user.username}' now has active access to: {[a.name for a in user_apps]}")
        assert slack_app.name in [a.name for a in user_apps]
        
        # 5. Revoke Access
        req_approved.status = 'Revoked'
        req_approved.comments = "Project completed, revoking communication channel access."
        db.session.commit()
        print(f"\nAdmin revoked access (Comments: '{req_approved.comments}')")
        
        req_revoked = AccessRequest.query.filter_by(user_id=regular_user.id, application_id=slack_app.id).first()
        assert req_revoked.status == 'Revoked'
        
        user_approved_reqs = AccessRequest.query.filter_by(user_id=regular_user.id, status='Approved').all()
        user_apps = [r.application for r in user_approved_reqs]
        print(f"User '{regular_user.username}' now has active access to: {[a.name for a in user_apps]}")
        assert slack_app.name not in [a.name for a in user_apps]
        
        print("\n--- VERIFICATION FLOW COMPLETED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_workflow()
