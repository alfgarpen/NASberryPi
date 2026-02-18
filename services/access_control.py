"""
access_control.py
-----------------
Centralized access control functions for NASberryPi.
All path and permission validation must go through these functions.
"""
import os
from utils import safe_join


def get_user_root(user, nas_root):
    """
    Returns the filesystem root that a user is allowed to browse.
    - Admins get the full NAS_ROOT.
    - Regular users get NAS_ROOT/users/<username>.
    """
    if user.role == 'admin':
        return nas_root
    return os.path.join(nas_root, 'users', user.username)


def get_user_root_rel(user):
    """
    Returns the relative path (from NAS_ROOT) of the user's root.
    Used for URL construction and path prefix checks.
    - Admins: '' (root)
    - Users: 'users/<username>'
    """
    if user.role == 'admin':
        return ''
    return f'users/{user.username}'


def get_user_home_rel(user):
    """
    Returns the relative path (from NAS_ROOT) of the user's personal home folder.
    - Always: 'users/<username>'
    """
    return f'users/{user.username}'


def check_shared_access(user):
    """
    Returns the SharedAccessRequest for a user, or None if no request exists.
    The caller can inspect .status ('pending', 'approved', 'rejected').
    Admins always have access (returns a sentinel with status='approved').
    """
    if user.role == 'admin':
        return _AdminAccessSentinel()

    from models import SharedAccessRequest
    return SharedAccessRequest.query.filter_by(user_id=user.id).first()


class _AdminAccessSentinel:
    """Sentinel object returned for admins so callers can uniformly check .status."""
    status = 'approved'


def ensure_path_allowed(user, req_path, nas_root):
    """
    Validates that req_path is within the user's allowed scope.

    Returns (is_allowed: bool, reason: str | None)

    Rules:
    - Admins can access any path under nas_root.
    - Regular users can access:
        - Their own home: users/<username>/...
        - The shared folder: shared/... (only if SharedAccessRequest.status == 'approved')
    - Path traversal is always blocked via safe_join.
    """
    # Normalize: strip leading slashes
    req_path = req_path.strip('/') if req_path else ''

    # Always validate the physical path stays inside nas_root
    abs_path = safe_join(nas_root, req_path)
    if abs_path is None:
        return False, 'Path traversal detected.'

    if user.role == 'admin':
        return True, None

    user_home_rel = get_user_home_rel(user)

    # Allow user's own home
    if req_path == user_home_rel or req_path.startswith(user_home_rel + '/'):
        return True, None

    # Allow shared folder if approved
    if req_path == 'shared' or req_path.startswith('shared/'):
        access = check_shared_access(user)
        if access and access.status == 'approved':
            return True, None
        elif access and access.status == 'pending':
            return False, 'pending'
        elif access and access.status == 'rejected':
            return False, 'rejected'
        else:
            return False, 'no_request'

    return False, 'Access denied to this path.'
