import os
from models import User

def ensure_storage_structure(app):
    """
    Ensures that the basic storage structure and all user directories exist.
    This function is idempotent and should be called during application startup.
    """
    nas_root = app.config['NAS_ROOT']
    users_dir = os.path.join(nas_root, 'users')
    shared_dir = os.path.join(nas_root, 'shared')

    # 1. Ensure base directories exist
    for d in [nas_root, users_dir, shared_dir]:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"Created directory: {d}")

    # 2. Sync user directories
    # We assume this is called within an app_context
    all_users = User.query.all()
    for user in all_users:
        user_home = os.path.join(users_dir, user.username)
        if not os.path.exists(user_home):
            os.makedirs(user_home)
            print(f"Created home directory for user: {user.username}")
