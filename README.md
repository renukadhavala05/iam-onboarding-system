# ZT-IAM: Zero Trust Identity & Access Management Platform

## Overview

ZT-IAM is a Flask-based Identity and Access Management (IAM) platform designed to simulate enterprise-grade identity governance and administration workflows. The project focuses on the complete Joiner-Mover-Leaver (JML) lifecycle while implementing Role-Based Access Control (RBAC), application access governance, approval workflows, audit logging, and Zero Trust security principles.

The platform enables organizations to manage user identities, application access, access reviews, approval processes, and lifecycle events through a centralized administrative dashboard.

---

## Key Features

### Identity Lifecycle Management (JML)

#### Joiner

* Create and onboard new users
* Assign organizational roles
* Provision access based on role

#### Mover

* Modify user information
* Change roles and permissions
* Update application assignments

#### Leaver

* Deactivate user accounts
* Revoke application access
* Remove user permissions

---

## Role-Based Access Control (RBAC)

* Admin role management
* Department-based access control
* Least privilege access principles
* Dynamic role assignment

---

## Application Access Governance

Supported application catalog includes:

* AWS
* Microsoft 365
* GitHub
* Jira
* Slack
* Salesforce

Features:

* Application catalog management
* Application assignment tracking
* Direct application assignment
* Application access revocation

---

## Access Request Workflow

Users can:

* Request application access
* Track request status

Administrators can:

* Review requests
* Approve requests
* Reject requests
* Assign applications automatically after approval

---

## Access Reviews

The platform supports periodic access certification through:

* Pending review tracking
* User access validation
* Permission recertification
* Access removal recommendations

---

## Expiration-Based Access Management

* Temporary access assignment
* Expiry date configuration
* Automatic access revocation
* Expiring access monitoring

---

## Audit Logging & Monitoring

The platform records:

* User logins
* Access requests
* Access approvals
* Role modifications
* User provisioning events
* User deprovisioning events
* Administrative actions

---

## Dashboard Analytics

Administrative dashboard provides:

* Total Users
* Active Users
* Locked Users
* Pending Reviews
* Expiring Access
* Direct Assignments
* Access Request Metrics

---

## Security Features

* Password Hashing
* Account Locking
* Session Management
* Audit Logging
* Route Protection
* Role-Based Authorization
* Zero Trust Security Principles

---

## Technology Stack

### Backend

* Python
* Flask
* Flask-SQLAlchemy

### Database

* SQLite

### Frontend

* HTML
* CSS
* JavaScript

### Security

* JWT Authentication
* PyOTP
* RBAC
* Audit Logging

---

## Project Architecture

```text
ZT-IAM
│
├── Identity Management
│   ├── User Provisioning
│   ├── User Modification
│   └── User Deprovisioning
│
├── Access Governance
│   ├── Access Requests
│   ├── Access Reviews
│   ├── Application Assignments
│   └── Access Expiration
│
├── Security
│   ├── Authentication
│   ├── Authorization
│   ├── RBAC
│   └── Audit Logging
│
└── Administration
    ├── Dashboard Analytics
    ├── User Management
    ├── Application Management
    └── Monitoring
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/renukadhavala05/iam-onboarding-system.git
```

### Navigate to Project Folder

```bash
cd iam-onboarding-system
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python app.py
```

---

## Future Enhancements

* Keycloak Integration
* Single Sign-On (SSO)
* SAML Authentication
* OpenID Connect (OIDC)
* LDAP Integration
* Microsoft Entra ID Integration
* Okta Integration
* Cloud Deployment
* Real Application Connectors

---

## Learning Outcomes

This project demonstrates practical understanding of:

* Identity and Access Management (IAM)
* Joiner-Mover-Leaver Lifecycle
* Role-Based Access Control (RBAC)
* Identity Governance and Administration (IGA)
* Access Request Workflows
* Access Certification
* Audit and Compliance
* Zero Trust Security Principles

---

## Author

**Renuka D**

B.Tech – Computer Science & Engineering (Cybersecurity)

Passionate about Identity & Access Management (IAM), Identity Governance, Zero Trust Security, and Cybersecurity.
