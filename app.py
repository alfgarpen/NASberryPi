import os
import shutil
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, send_from_directory, jsonify)
from config import Config
from utils import get_disk_usage, safe_join
from models import db, User
from services.access_control import (get_user_root, get_user_root_rel,
                                     check_shared_access, ensure_path_allowed)
from services.user_service import reset_user_password, change_user_role

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database
db.init_app(app)

# Create storage directories if they don't exist
USERS_DIR = os.path.join(app.config['NAS_ROOT'], 'users')
SHARED_DIR = os.path.join(app.config['NAS_ROOT'], 'shared')

for d in [USERS_DIR, SHARED_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

with app.app_context():
    db.create_all()
    # Create default admin if no users exist
    if not User.query.first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

from disk_manager import disk_manager

@disk_manager.before_request
def restrict_disk_manager():
    if 'logged_in' not in session:
        return redirect(url_for('login', next=request.url))
    if session.get('role') != 'admin':
        flash('Access denied. Administrator privileges required.', 'danger')
        return render_template('access_denied.html'), 403

app.register_blueprint(disk_manager, url_prefix='/')

# ─────────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('Access denied. Administrator privileges required.', 'danger')
            return render_template('access_denied.html'), 403
        return f(*args, **kwargs)
    return decorated_function


def _get_current_user():
    """Helper: fetch the User object for the currently logged-in session.
    Returns None if the user no longer exists (e.g. stale session after DB reset).
    Routes that call this should handle None by clearing the session.
    """
    return User.query.filter_by(username=session.get('username')).first()


def _require_user():
    """Returns the current User or triggers a session-clearing redirect.
    Use this in routes that need the user object and cannot proceed without it.
    Returns (user, None) on success, or (None, redirect_response) on failure.
    """
    user = _get_current_user()
    if user is None:
        session.clear()
        flash('Session expired. Please log in again.', 'warning')
        return None, redirect(url_for('login'))
    return user, None


# ─────────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user.role

            # Force password change if flagged
            if user.must_change_password:
                flash('Your password has been reset. Please set a new password.', 'warning')
                return redirect(url_for('change_password'))

            flash('Login successful', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    user, err = _require_user()
    if err:
        return err
    if request.method == 'POST':
        new_password = request.form.get('new_password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        if not new_password or len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
        elif new_password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            user.set_password(new_password)
            user.must_change_password = False
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('dashboard'))

    return render_template('change_password.html')


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    user, err = _require_user()
    if err:
        return err
    disk_usage = get_disk_usage(app.config['NAS_ROOT'])
    shared_req = check_shared_access(user)
    return render_template('dashboard.html', disk=disk_usage, shared_req=shared_req)


# ─────────────────────────────────────────────
# File Browser
# ─────────────────────────────────────────────

@app.route('/files')
@app.route('/files/<path:req_path>')
@login_required
def files(req_path=''):
    user, err = _require_user()
    if err:
        return err
    nas_root = app.config['NAS_ROOT']
    user_root_rel = get_user_root_rel(user)

    # Default path handling
    if not req_path or req_path == '.':
        if user.role == 'admin':
            # Admin root is NAS_ROOT itself — serve it directly, no redirect needed
            req_path = ''
        else:
            # Regular users redirect to their home directory
            return redirect(url_for('files', req_path=user_root_rel))

    # Centralized access check (skip for admin at root — always allowed)
    if req_path:
        is_allowed, reason = ensure_path_allowed(user, req_path, nas_root)
        if not is_allowed:
            if reason == 'pending':
                flash('Your shared folder access request is pending approval.', 'info')
            elif reason == 'rejected':
                flash('Your shared folder access request was rejected.', 'danger')
            elif reason == 'no_request':
                flash('You have not requested access to the shared folder.', 'warning')
            else:
                flash(reason or 'Access denied.', 'danger')
            return redirect(url_for('files', req_path=user_root_rel))

    # Resolve physical path
    abs_path = safe_join(nas_root, req_path)
    if not abs_path or not os.path.exists(abs_path):
        flash('Path not found.', 'danger')
        return redirect(url_for('files', req_path=user_root_rel))

    # Serve file directly
    if os.path.isfile(abs_path):
        return send_from_directory(os.path.dirname(abs_path),
                                   os.path.basename(abs_path),
                                   as_attachment=True)

    # List directory contents
    contents = []
    try:
        with os.scandir(abs_path) as it:
            for entry in it:
                is_dir = entry.is_dir()
                size = entry.stat().st_size if not is_dir else 0
                rel_path = os.path.relpath(entry.path, nas_root).replace('\\', '/')
                contents.append({
                    'name': entry.name,
                    'is_dir': is_dir,
                    'size': f'{size / (1024 * 1024):.2f} MB' if not is_dir else '-',
                    'path': rel_path,
                })
    except PermissionError:
        flash('Permission denied accessing this directory.', 'danger')

    contents.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    # Calculate parent path (never let user escape their root)
    parent_path = None
    if req_path and req_path != user_root_rel and req_path != 'shared':
        candidate = os.path.dirname(req_path.rstrip('/'))
        # Verify parent is still within allowed scope
        p_allowed, _ = ensure_path_allowed(user, candidate, nas_root)
        if p_allowed:
            parent_path = candidate if candidate else None

    # Shared folder access info for the template
    shared_access = check_shared_access(user)

    return render_template(
        'files.html',
        files=contents,
        current_path=req_path,
        parent_path=parent_path,
        user_root_rel=user_root_rel,
        shared_access=shared_access,
    )


# ─────────────────────────────────────────────
# File Actions
# ─────────────────────────────────────────────

@app.route('/file/action', methods=['POST'])
@login_required
def file_action():
    action = request.form.get('action')
    current_path = request.form.get('current_path', '')
    user, err = _require_user()
    if err:
        return err
    nas_root = app.config['NAS_ROOT']

    # Centralized access check for the current directory
    is_allowed, reason = ensure_path_allowed(user, current_path, nas_root)
    if not is_allowed:
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403

    full_current_dir = safe_join(nas_root, current_path)
    if not full_current_dir:
        return jsonify({'status': 'error', 'message': 'Invalid path'}), 400

    if action == 'upload':
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        filename = file.filename  # Use secure_filename in production
        file.save(os.path.join(full_current_dir, filename))
        flash(f'File {filename} uploaded successfully.', 'success')
        return redirect(url_for('files', req_path=current_path))

    elif action == 'create_folder':
        folder_name = request.form.get('folder_name', '').strip()
        if folder_name:
            new_folder = os.path.join(full_current_dir, folder_name)
            try:
                os.makedirs(new_folder)
                flash(f'Folder "{folder_name}" created.', 'success')
            except FileExistsError:
                flash('Folder already exists.', 'warning')
            except Exception as e:
                flash(f'Error creating folder: {e}', 'danger')
        return redirect(url_for('files', req_path=current_path))

    elif action == 'rename':
        old_name = request.form.get('old_name', '').strip()
        new_name = request.form.get('new_name', '').strip()
        if old_name and new_name:
            try:
                os.rename(os.path.join(full_current_dir, old_name),
                          os.path.join(full_current_dir, new_name))
                flash(f'Renamed "{old_name}" to "{new_name}".', 'success')
            except Exception as e:
                flash(f'Error renaming: {e}', 'danger')
        return redirect(url_for('files', req_path=current_path))

    elif action == 'delete':
        item_name = request.form.get('item_name', '').strip()
        if item_name:
            item_path = os.path.join(full_current_dir, item_name)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                flash(f'Deleted "{item_name}".', 'success')
            except Exception as e:
                flash(f'Error deleting: {e}', 'danger')
        return redirect(url_for('files', req_path=current_path))

    return redirect(url_for('files', req_path=current_path))


# ─────────────────────────────────────────────
# Admin – User Management
# ─────────────────────────────────────────────

@app.route('/users')
@admin_required
def users():
    nas_users = User.query.order_by(User.username).all()
    return render_template('users.html', users=nas_users)


@app.route('/user/action', methods=['POST'])
@admin_required
def user_action():
    action = request.form.get('action')

    if action == 'create':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('Username and password are required.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('User already exists.', 'warning')
        else:
            new_user = User(username=username, role='user')
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            # Create user storage directory
            user_home = os.path.join(USERS_DIR, username)
            if not os.path.exists(user_home):
                os.makedirs(user_home)
            flash(f'User "{username}" created successfully.', 'success')

    elif action == 'delete':
        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        if user:
            if user.username == session.get('username'):
                flash('You cannot delete your own account.', 'danger')
            else:
                db.session.delete(user)
                db.session.commit()
                flash(f'User "{user.username}" deleted.', 'success')

    elif action == 'change_role':
        user_id = request.form.get('user_id')
        new_role = request.form.get('new_role')
        user = User.query.get(user_id)
        if user:
            try:
                change_user_role(user, new_role, session.get('username'), db.session)
                flash(f'Role for "{user.username}" changed to "{new_role}".', 'success')
            except ValueError as e:
                flash(str(e), 'danger')

    elif action == 'reset_password':
        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        if user:
            temp_pw = reset_user_password(user, db.session)
            flash(
                f'Password for "{user.username}" reset. '
                f'Temporary password (shown once): <strong>{temp_pw}</strong>',
                'warning'
            )

    return redirect(url_for('users'))


# ─────────────────────────────────────────────
# Admin – Shared Access Requests
# ─────────────────────────────────────────────

@app.route('/request_shared_access', methods=['POST'])
@login_required
def request_shared_access():
    from models import SharedAccessRequest
    user, err = _require_user()
    if err:
        return err

    existing = SharedAccessRequest.query.filter_by(user_id=user.id).first()
    if existing:
        if existing.status == 'approved':
            flash('You already have access to the shared folder.', 'info')
        elif existing.status == 'pending':
            flash('Your request is still pending approval.', 'info')
        else:
            existing.status = 'pending'
            db.session.commit()
            flash('Access request resent.', 'success')
    else:
        db.session.add(SharedAccessRequest(user_id=user.id))
        db.session.commit()
        flash('Access request submitted.', 'success')

    return redirect(url_for('dashboard'))


@app.route('/admin/requests')
@admin_required
def admin_requests():
    from models import SharedAccessRequest
    reqs = SharedAccessRequest.query.all()
    return render_template('shared_requests.html', requests=reqs)


@app.route('/admin/request/<int:req_id>/<action>', methods=['POST'])
@admin_required
def shared_request_action(req_id, action):
    from models import SharedAccessRequest
    req = SharedAccessRequest.query.get_or_404(req_id)

    if action == 'approve':
        req.status = 'approved'
        flash(f'Access approved for "{req.user.username if req.user else "unknown"}".', 'success')
    elif action == 'reject':
        req.status = 'rejected'
        flash(f'Access rejected for "{req.user.username if req.user else "unknown"}".', 'warning')

    db.session.commit()
    return redirect(url_for('admin_requests'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
