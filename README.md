# IAM Automated User Onboarding System

A Flask-based Identity and Access Management (IAM) application designed to simulate secure enterprise-level user onboarding and access management workflows.

The system provides authentication, role-based access control (RBAC), multi-factor authentication support, user management, and activity logging through an interactive admin dashboard.

---

## Features

- Secure User Registration & Login
- Role-Based Access Control (RBAC)
- Admin Dashboard
- Multi-Factor Authentication (MFA)
- Password Reset Functionality
- User Profile Management
- Activity & Audit Logging
- Route Protection using Middleware
- SQLite Database Integration

---

## Technologies Used

- Python
- Flask
- Flask-SQLAlchemy
- HTML / CSS / JavaScript
- SQLite
- PyOTP (MFA)
- JWT Authentication

---

## Project Structure

```bash
iam_onboarding_project/
│
├── app.py
├── config.py
├── middleware.py
├── requirements.txt
│
├── models/
├── routes/
├── templates/
├── static/
├── logs/
└── scratch/
```

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/renukadhavala05/iam-onboarding-system.git
```

### 2. Navigate to Project Folder

```bash
cd iam-onboarding-system
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

---

## Example Roles

- Admin
- Developer
- HR
- Finance
- Intern

---

## Future Enhancements

- LDAP Integration
- OAuth / SSO Support
- Cloud Deployment
- Email Verification
- Advanced Audit Analytics

---

## Author

Renuka D  
B.Tech CSE (Cybersecurity)
