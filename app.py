import os
import shutil
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from config import Config
from utils import get_disk_usage, get_system_users, safe_join

app = Flask(__name__)
app.config.from_object(Config)

# Ensure NAS Root exists
if not os.path.exists(app.config['NAS_ROOT']):
    os.makedirs(app.config['NAS_ROOT'])

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple dictionary lookup for demo purposes
        # In real app: Use database & hashed passwords
        user_password = app.config['USERS'].get(username)
        
        if user_password and user_password == password:
            session['logged_in'] = True
            session['username'] = username
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

@app.route('/')
@login_required
def dashboard():
    disk_usage = get_disk_usage(app.config['NAS_ROOT'])
    return render_template('dashboard.html', disk=disk_usage)

@app.route('/files')
@app.route('/files/<path:req_path>')
@login_required
def files(req_path=''):
    # Safe path handling
    abs_path = safe_join(app.config['NAS_ROOT'], req_path)
    
    if not abs_path or not os.path.exists(abs_path):
        flash('Invalid path', 'danger')
        return redirect(url_for('files'))

    # If it's a file, serve it
    if os.path.isfile(abs_path):
        directory = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)
        return send_from_directory(directory, filename, as_attachment=True)

    # It's a directory: List contents
    contents = []
    try:
        with os.scandir(abs_path) as it:
            for entry in it:
                is_dir = entry.is_dir()
                size = entry.stat().st_size if not is_dir else 0
                # Rel path for links
                rel_path = os.path.relpath(entry.path, app.config['NAS_ROOT'])
                
                contents.append({
                    'name': entry.name,
                    'is_dir': is_dir,
                    'size': f"{size / (1024*1024):.2f} MB" if not is_dir else "-",
                    'path': rel_path
                })
    except PermissionError:
        flash('Permission denied accessing this directory', 'danger')
    
    # Sort: Folders first, then files
    contents.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    # Calculate parent path for "Go Up" button
    parent_path = None
    if req_path and req_path != '.':
        parent_path = os.path.dirname(req_path.rstrip('/'))
        if parent_path == '':
            parent_path = None # Shows link to root /files
            
    return render_template('files.html', files=contents, current_path=req_path, parent_path=parent_path)

@app.route('/file/action', methods=['POST'])
@login_required
def file_action():
    action = request.form.get('action')
    current_path = request.form.get('current_path', '')
    
    full_current_dir = safe_join(app.config['NAS_ROOT'], current_path)
    if not full_current_dir:
         return jsonify({'status': 'error', 'message': 'Invalid current path'}), 400

    if action == 'upload':
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        if file:
            filename = file.filename # In prod use secure_filename
            save_path = os.path.join(full_current_dir, filename)
            file.save(save_path)
            flash(f'File {filename} uploaded successfully', 'success')
            return redirect(url_for('files', req_path=current_path))

    elif action == 'create_folder':
        folder_name = request.form.get('folder_name')
        if folder_name:
            new_folder_path = os.path.join(full_current_dir, folder_name)
            try:
                os.makedirs(new_folder_path)
                flash(f'Folder {folder_name} created', 'success')
            except FileExistsError:
                flash('Folder already exists', 'warning')
            except Exception as e:
                flash(f'Error creating folder: {e}', 'danger')
        return redirect(url_for('files', req_path=current_path))
        
    elif action == 'rename':
        old_name = request.form.get('old_name')
        new_name = request.form.get('new_name')
        if old_name and new_name:
            old_path = os.path.join(full_current_dir, old_name)
            new_path = os.path.join(full_current_dir, new_name)
            try:
                os.rename(old_path, new_path)
                flash(f'Renamed {old_name} to {new_name}', 'success')
            except Exception as e:
                flash(f'Error renaming: {e}', 'danger')
        return redirect(url_for('files', req_path=current_path))

    elif action == 'delete':
        item_name = request.form.get('item_name')
        if item_name:
            item_path = os.path.join(full_current_dir, item_name)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                flash(f'Deleted {item_name}', 'success')
            except Exception as e:
                 flash(f'Error deleting: {e}', 'danger')
        return redirect(url_for('files', req_path=current_path))

    return redirect(url_for('files', req_path=current_path))

@app.route('/users')
@login_required
def users():
    system_users = get_system_users()
    return render_template('users.html', users=system_users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
