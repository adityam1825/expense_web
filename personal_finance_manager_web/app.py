# app.py

from dotenv import load_dotenv # Import load_dotenv
load_dotenv() # Load environment variables from .env file FIRST

import os
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, current_user, login_required

# Import configurations and database instance
from config import Config
from database import db

# Import your models
# Ensure all models are imported for db.create_all() if you uncomment it below
from models import User, Category # Only import models you've defined and are using

# Import Blueprints you ARE using
from routes.auth import auth_bp
from routes.budgets import budgets_bp
from routes.categories import categories_bp
# from routes.transactions import transactions_bp # COMMENTED OUT
# from routes.reports import reports_bp         # COMMENTED OUT

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login' # Specify the login view for redirection
    login_manager.init_app(app)

    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- DATABASE TABLE CREATION (UNCOMMENT THIS ONLY ONCE FOR INITIAL SETUP!) ---
    with app.app_context():
        # db.create_all() # UNCOMMENT THIS LINE ONLY ONCE FOR INITIAL TABLE CREATION
        pass # Keep 'pass' if db.create_all() is commented out
    # ---------------------------------------------------------------------------

    # --- Register Blueprints ---
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(budgets_bp, url_prefix='/budgets')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    # app.register_blueprint(transactions_bp, url_prefix='/transactions') # COMMENTED OUT
    # app.register_blueprint(reports_bp, url_prefix='/reports')         # COMMENTED OUT

    # --- Global Routes ---
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/dashboard')
    @login_required
    def dashboard_page():
        # This page will be less functional for now without transactions/reports
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