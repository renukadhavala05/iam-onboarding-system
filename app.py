import os
from flask import Flask, session
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

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)