"""
user_service.py
---------------
Business logic for user management in NASberryPi.
Routes should call these functions instead of implementing logic inline.
"""
import secrets
import string
from werkzeug.security import generate_password_hash


def generate_temp_password(length=12):
    """
    Generates a cryptographically secure random temporary password.
    Contains uppercase, lowercase, digits, and safe symbols.
    """
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def reset_user_password(user, db_session):
    """
    Resets a user's password to a secure random temporary password.
    Sets must_change_password=True to force change on next login.

    Returns the plain-text temporary password (show once, never store).
    """
    temp_password = generate_temp_password()
    user.password_hash = generate_password_hash(temp_password)
    user.must_change_password = True
    db_session.commit()
    return temp_password


def change_user_role(user, new_role, current_admin_username, db_session):
    """
    Changes a user's role.
    Raises ValueError if an admin tries to demote themselves.
    Returns True on success.
    """
    if user.username == current_admin_username and new_role != 'admin':
        raise ValueError('You cannot remove your own admin role.')

    if new_role not in ('admin', 'user'):
        raise ValueError(f'Invalid role: {new_role}')

    user.role = new_role
    db_session.commit()
    return True
