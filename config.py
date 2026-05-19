import os

class Config:
    SECRET_KEY = "supersecretkey"
    SQLALCHEMY_DATABASE_URI = "sqlite:///database.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_FILE = os.path.join("logs", "logs.txt")
    PERMANENT_SESSION_LIFETIME = 1800 # 30 minutes