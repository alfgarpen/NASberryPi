# Naspberry PI - Python NAS

A lightweight, Flask-based NAS administration tool for home or small office environments.

## Features
- **Dashboard**: View real-time disk usage statistics.
- **File Manager**: Web-based file explorer to list, upload, create folders, rename, and delete files.
- **User Management**: View local system users.
- **Secure**: Session-based authentication and path traversal protection.

## Installation

1. **Prerequisites**
   - Python 3.x
   - Linux environment (recommended)

2. **Setup**
   Clone or copy the project files to your device.

   ```bash
   cd /path/to/project
   ```

3. **Install Dependencies**
   It is recommended to use a virtual environment.

   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate it
   source venv/bin/activate
   
   # Install Flask
   pip install Flask
   ```

## Configuration
Edit `config.py` to customize settings:
- `NAS_ROOT`: The directory you want to share (defaults to `./nas_data`).
- `USERS`: Dictionary of `username: password` for access control.
- `SECRET_KEY`: Change this for production security.

## Usage
1. **Start the Server**
   ```bash
   python app.py
   ```

2. **Access the Interface**
   Open your browser and navigate to:
   `http://localhost:5000`

3. **Login**
   - Default Username: `admin`
   - Default Password: `admin123`

## Project Structure
- `app.py`: Main application logic.
- `config.py`: Configuration settings.
- `utils.py`: Helper functions for system interactions.
- `templates/`: HTML files for the frontend.
- `static/`: CSS and other static assets.
- `nas_data/`: Default storage directory.
