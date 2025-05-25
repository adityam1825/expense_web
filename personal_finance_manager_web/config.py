# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask Secret Key for session management and security
    # Loaded from .env for security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_fallback_secret_key_if_env_not_found'

    # Database Configuration (PostgreSQL)
    # Loaded from .env
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'postgresql://user:password@localhost:5432/default_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Suppress a warning

    # Debug mode (set to False in production)
    DEBUG = True