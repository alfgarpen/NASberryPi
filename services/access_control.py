"""
access_control.py
-----------------
Centralized access control functions for NASberryPi.
ALL path and permission validation MUST go through these functions.
The frontend only reflects these decisions; backend is the single source of truth.

Permission model:
  - users/<username>/...  → implicitly private (path-based). Only owner + admin.
  - shared/...            → granular per-file (FilePermission in DB).
      Defaults on upload: can_read=True, can_write=True, can_delete=False
      Only owner or admin can delete unless can_delete is explicitly True for all.
"""
import logging
import os
from datetime import datetime

from utils import safe_join

# ─── Audit logger ───────────────────────────────────────────────────────────

_audit_logger = logging.getLogger('nas.access')


def _setup_audit_log(nas_root: str):
    """
    Lazily initialise a file handler for the audit log so it ends up in nas_data/.
    Called once at first use (safe to call multiple times).
    """
    if _audit_logger.handlers:
        return
    log_path = os.path.join(nas_root, 'access_denied.log')
    try:
        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%Y-%m-%d %H:%M:%S'))
        _audit_logger.addHandler(fh)
        _audit_logger.setLevel(logging.WARNING)
    except OSError:
        # If the log file can't be created (e.g. not yet mounted), fall back to stderr
        _audit_logger.addHandler(logging.StreamHandler())
        _audit_logger.setLevel(logging.WARNING)


def log_access_denied(user, rel_path: str, action: str, nas_root: str):
    """
    Write a line to nas_data/access_denied.log whenever an unauthorised action
    is attempted.  Also prints to stderr via the root logger.
    """
    _setup_audit_log(nas_root)
    _audit_logger.warning(
        'DENIED | user=%s | action=%s | path=%s',
        getattr(user, 'username', '?'), action, rel_path
    )


# ─── Path helpers ────────────────────────────────────────────────────────────

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
    - Admins: '' (root)
    - Users:  'users/<username>'
    """
    if user.role == 'admin':
        return ''
    return f'users/{user.username}'


def get_user_home_rel(user):
    """Always returns 'users/<username>'."""
    return f'users/{user.username}'


# ─── Shared access requests ──────────────────────────────────────────────────

def check_shared_access(user):
    """
    Returns the SharedAccessRequest for a user, or None if no request exists.
    Admins always have access (returns a sentinel with status='approved').
    """
    if user.role == 'admin':
        return _AdminAccessSentinel()

    from models import SharedAccessRequest
    return SharedAccessRequest.query.filter_by(user_id=user.id).first()


class _AdminAccessSentinel:
    """Sentinel object returned for admins so callers can uniformly check .status."""
    status = 'approved'


# ─── Path-level access check ─────────────────────────────────────────────────

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
    req_path = req_path.strip('/') if req_path else ''

    abs_path = safe_join(nas_root, req_path)
    if abs_path is None:
        return False, 'Path traversal detected.'

    if user.role == 'admin':
        return True, None

    user_home_rel = get_user_home_rel(user)

    if req_path == user_home_rel or req_path.startswith(user_home_rel + '/'):
        return True, None

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


# ─── Granular file-level permission checks ───────────────────────────────────

def _get_file_permission(rel_path: str):
    """
    Internal: look up a FilePermission record by normalized rel_path.
    Returns the ORM object or None.
    """
    from models import FilePermission
    norm = rel_path.strip('/')
    return FilePermission.query.filter_by(rel_path=norm).first()


def can_user_read(user, rel_path: str, nas_root: str) -> bool:
    """
    Returns True if `user` is allowed to read/download `rel_path`.

    Rules:
    - Admin → always True.
    - users/<X>/... → only user with username == X.
    - shared/... → True if approved + FilePermission.can_read (or no record → default True)
                   False if visibility == 'private' and user is not the owner.
    """
    if user.role == 'admin':
        return True

    norm = rel_path.strip('/')

    # Private home directory
    user_home_rel = get_user_home_rel(user)
    if norm == user_home_rel or norm.startswith(user_home_rel + '/'):
        return True  # own files: always readable

    # Another user's home directory
    if norm.startswith('users/'):
        return False

    # Shared area
    if norm == 'shared' or norm.startswith('shared/'):
        access = check_shared_access(user)
        if not (access and access.status == 'approved'):
            return False

        fp = _get_file_permission(norm)
        if fp is None:
            return True  # no record → default: readable
        if fp.visibility == 'private' and (fp.owner_id != user.id):
            return False
        return fp.can_read

    return False


def can_user_write(user, rel_path: str, nas_root: str) -> bool:
    """
    Returns True if `user` is allowed to write (upload/rename/overwrite) `rel_path`.

    Rules:
    - Admin → always True.
    - users/<X>/... → only user X.
    - shared/... → owner, or can_write == True for approved users.
    """
    if user.role == 'admin':
        return True

    norm = rel_path.strip('/')

    user_home_rel = get_user_home_rel(user)
    if norm == user_home_rel or norm.startswith(user_home_rel + '/'):
        return True

    if norm.startswith('users/'):
        return False

    if norm == 'shared' or norm.startswith('shared/'):
        access = check_shared_access(user)
        if not (access and access.status == 'approved'):
            return False

        fp = _get_file_permission(norm)
        if fp is None:
            return True  # default: writable
        if fp.visibility == 'private' and (fp.owner_id != user.id):
            return False
        # Owner can always write their own file
        if fp.owner_id == user.id:
            return True
        return fp.can_write

    return False


def can_user_delete(user, rel_path: str, nas_root: str) -> bool:
    """
    Returns True if `user` is allowed to delete `rel_path`.

    Rules:
    - Admin → always True.
    - users/<X>/... → only user X.
    - shared/... → owner always; other approved users only if can_delete == True.
    """
    if user.role == 'admin':
        return True

    norm = rel_path.strip('/')

    user_home_rel = get_user_home_rel(user)
    if norm == user_home_rel or norm.startswith(user_home_rel + '/'):
        return True

    if norm.startswith('users/'):
        return False

    if norm == 'shared' or norm.startswith('shared/'):
        access = check_shared_access(user)
        if not (access and access.status == 'approved'):
            return False

        fp = _get_file_permission(norm)
        if fp is None:
            # No record → only owner could delete, but we have no owner info
            # Default: deny delete for unknown shared files (safe default)
            return False
        if fp.owner_id == user.id:
            return True
        if fp.visibility == 'private':
            return False
        return fp.can_delete

    return False


# ─── Upload registration ──────────────────────────────────────────────────────

def register_upload(user, rel_path: str, db_session):
    """
    Create or update a FilePermission record when a file is uploaded to shared/.
    Called by the upload route after saving the file to disk.

    Only creates a record for paths inside shared/; no-ops otherwise.
    """
    norm = rel_path.strip('/')
    if not (norm == 'shared' or norm.startswith('shared/')):
        return  # Private area — no DB record needed

    from models import FilePermission
    fp = FilePermission.query.filter_by(rel_path=norm).first()
    if fp is None:
        fp = FilePermission(
            rel_path=norm,
            owner_id=user.id,
            visibility='shared',
            can_read=True,
            can_write=True,
            can_delete=False,
        )
        db_session.add(fp)
    else:
        # Re-upload: update owner (new uploader takes ownership)
        fp.owner_id = user.id
        fp.created_at = datetime.utcnow()
    db_session.commit()


def rename_permission_record(old_rel: str, new_rel: str, db_session):
    """
    Update the rel_path in FilePermission when a file is renamed/moved.
    No-op if no record exists.
    """
    from models import FilePermission
    fp = FilePermission.query.filter_by(rel_path=old_rel.strip('/')).first()
    if fp:
        fp.rel_path = new_rel.strip('/')
        db_session.commit()


def delete_permission_record(rel_path: str, db_session):
    """
    Remove the FilePermission record when a file is deleted.
    No-op if no record exists.
    """
    from models import FilePermission
    fp = FilePermission.query.filter_by(rel_path=rel_path.strip('/')).first()
    if fp:
        db_session.delete(fp)
        db_session.commit()
