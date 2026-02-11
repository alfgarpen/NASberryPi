import os
import shutil
import pwd

def get_disk_usage(path):
    """
    Returns disk usage statistics for the file system containing path.
    Returns a dictionary with 'total', 'used', 'free' in GB and 'percent'.
    """
    try:
        total, used, free = shutil.disk_usage(path)
        
        # Convert to GB
        gb = 1024 ** 3
        return {
            'total': round(total / gb, 2),
            'used': round(used / gb, 2),
            'free': round(free / gb, 2),
            'percent': round((used / total) * 100, 1)
        }
    except Exception as e:
        print(f"Error getting disk usage: {e}")
        return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}

def get_system_users():
    """
    Returns a list of system users.
    Filters for users with UID >= 1000 usually denoting human users,
    and ensures they have a valid shell.
    """
    users = []
    try:
        for p in pwd.getpwall():
            # Standard Linux check: UID >= 1000 and valid shell
            if p.pw_uid >= 1000 and 'nologin' not in p.pw_shell and 'false' not in p.pw_shell:
                users.append({
                    'username': p.pw_name,
                    'uid': p.pw_uid,
                    'gid': p.pw_gid,
                    'home': p.pw_dir,
                    'shell': p.pw_shell
                })
    except Exception as e:
        print(f"Error listing users: {e}")
    return users

def safe_join(root, path):
    """
    Safely joins a root directory and a user-provided path to prevent directory traversal.
    Returns the absolute path if safe, or None if unsafe.
    """
    # Normalize the path to prevent .. attacks
    if not path:
        return root
        
    full_path = os.path.abspath(os.path.join(root, path.strip('/')))
    
    # Ensure the final path starts with the root path
    if os.path.commonprefix([root, full_path]) == root:
        return full_path
    
    return None
