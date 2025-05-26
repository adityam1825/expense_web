# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_fallback_secret_key_if_env_not_loaded'

    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    # --- ADD THIS LINE FOR DEBUGGING ---
    print(f"DEBUG: SQLALCHEMY_DATABASE_URI loaded: {SQLALCHEMY_DATABASE_URI}")
    # -----------------------------------

    SQLALCHEMY_TRACK_MODIFICATIONS = False