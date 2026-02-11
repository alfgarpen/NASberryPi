import os

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key_very_secret_12345'
    
    # Root directory for the File Explorer
    # Defaults to 'nas_data' within the project folder if not specified
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    NAS_ROOT = os.environ.get('NAS_ROOT') or os.path.join(BASE_DIR, 'nas_data')
    
    # Simple User Dictionary for Authentication (Username: Password)
    # In a production environment, use hashed passwords and a database.
    USERS = {
        "admin": "admin123"
    }

    # Max upload size (e.g., 1GB)
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024
