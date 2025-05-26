# app.py
from flask import Flask, render_template, redirect, url_for, flash
from config import Config # Import your Config class
from database import db # Import the db object from database.py
from flask_login import LoginManager, current_user, login_required # Import Flask-Login components

# Import your User model for Flask-Login's user_loader
from models import User

# Import Blueprints
from routes.auth import auth_bp # Import your authentication blueprint

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) # Load configuration from Config class

    # Initialize extensions
    db.init_app(app) # Initialize SQLAlchemy with the Flask app

    # --- Flask-Login Setup ---
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login' # This tells Flask-Login where your login route is
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # This function tells Flask-Login how to load a user from the user_id stored in the session
        return User.query.get(int(user_id))
    # --- End Flask-Login Setup ---

    # --- DATABASE TABLE CREATION (UNCOMMENT ONLY ONCE FOR INITIAL SETUP!) ---
    # You MUST comment this out IMMEDIATELY after your tables are created.
    with app.app_context():
       db.create_all()
    # ---------------------------------------------------------------------

    # --- Register Blueprints ---
    app.register_blueprint(auth_bp, url_prefix='/auth')
    # Register other blueprints here as you create them:
    # app.register_blueprint(categories_bp, url_prefix='/categories')
    # app.register_blueprint(transactions_bp, url_prefix='/transactions')
    # app.register_blueprint(budgets_bp, url_prefix='/budgets')
    # app.register_blueprint(reports_bp, url_prefix='/reports')


    # --- Global Routes ---

    # NEW: Public Home Page Route
    @app.route('/')
    def home():
        # This page is accessible to everyone, logged in or not.
        # It's your website's landing page.
        return render_template('home.html')

    # RENAMED: User Dashboard Page Route (requires login)
    @app.route('/dashboard') # Changed from '/' to '/dashboard'
    @login_required # This decorator ensures only logged-in users can access this page
    def dashboard_page(): # Renamed the function
        # This is the main dashboard for authenticated users.
        return render_template('reports/dashboard.html', user=current_user)

    # --- Error Handlers (Good practice for user-friendly error pages) ---
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # Important: Rollback the session if a database error occurs
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) # debug=True enables auto-reloading and debug output