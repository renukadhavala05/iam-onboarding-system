"""
reset_users.py
==============
Run this script from the project root to wipe ALL user accounts,
their OTP secrets, linked emails, access requests and session data,
while KEEPING the 6 seeded enterprise applications intact.

Usage:
    python reset_users.py
"""

import sys
import os

# Make sure we can import the Flask app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.user_model import db, User, AccessRequest

def reset_users():
    app = create_app()
    with app.app_context():
        print("=" * 55)
        print("  IAM SYSTEM — USER DATA RESET")
        print("=" * 55)

        # Count what exists before deletion
        user_count = User.query.count()
        req_count  = AccessRequest.query.count()

        if user_count == 0:
            print("\n[INFO] No user accounts found. Database is already clean.")
        else:
            print(f"\n[INFO] Found {user_count} user account(s) and {req_count} access request(s).")
            print("\n  Users to be removed:")
            for u in User.query.all():
                print(f"    - {u.username} | {u.email or 'no email'} | role={u.role}")

            print("\n[INFO] Deleting all access requests...")
            AccessRequest.query.delete()

            print("[INFO] Deleting all user accounts (emails, OTP secrets, sessions)...")
            User.query.delete()

            db.session.commit()
            print(f"\n[SUCCESS] {user_count} user(s) and {req_count} access request(s) deleted.")

        from models.user_model import Application
        app_count = Application.query.count()
        print(f"[INFO] Application catalog preserved — {app_count} apps remain intact.")
        print("\n  Applications still in catalog:")
        for a in Application.query.all():
            status = "ACTIVE" if a.is_active else "DISABLED"
            print(f"    - {a.name} ({a.category}) [{status}]")

        print("\n[DONE] Database reset complete. You can now register a fresh admin account.")
        print("=" * 55)

if __name__ == "__main__":
    confirm = input("\nThis will permanently delete ALL user accounts.\nType 'YES' to confirm: ").strip()
    if confirm == "YES":
        reset_users()
    else:
        print("Aborted — no changes made.")
