# app.py (Use this version ONLY FOR DATABASE CREATION)
from flask import Flask, render_template, redirect, url_for, flash
from config import Config
from database import db
from flask_login import LoginManager, current_user, login_required

from models import User # Import User model

# Import Blueprints
from routes.auth import auth_bp
from routes.budgets import budgets_bp # Import your budgets blueprint
from routes.categories import categories_bp 

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- DATABASE TABLE CREATION (UNCOMMENT THIS ONLY ONCE!) ---
    with app.app_context():
        db.create_all() # <--- UNCOMMENT THIS LINE AND REMOVE THE 'pass' LINE BELOW
    # -----------------------------------------------------------

    # --- Register Blueprints ---
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(budgets_bp, url_prefix='/budgets')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    # Add other blueprints here as you create them

    # --- Global Routes ---
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/dashboard')
    @login_required
    def dashboard_page():
        return render_template('reports/dashboard.html', user=current_user)

    # --- Error Handlers ---
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback() # Rollback session on error
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)