import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
if not os.path.exists(INSTANCE_DIR):
    os.makedirs(INSTANCE_DIR, exist_ok=True)

class Config:
    SECRET_KEY = "supersecretkey"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_DIR, 'database.db').replace('\\', '/')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_FILE = os.path.join("logs", "logs.txt")
    PERMANENT_SESSION_LIFETIME = 1800 # 30 minutes