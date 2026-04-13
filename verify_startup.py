import os
import shutil
from app import app, db
from models import User
from services.initialization import ensure_storage_structure

def test_startup_consistency():
    print("Starting verification of startup consistency...")
    
    # 1. Setup temporary NAS_ROOT
    temp_nas_root = os.path.join(os.getcwd(), 'temp_nas_test')
    if os.path.exists(temp_nas_root):
        shutil.rmtree(temp_nas_root)
    
    app.config['NAS_ROOT'] = temp_nas_root
    
    with app.app_context():
        # Ensure we have at least the admin user
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Created admin user for test.")

        # Create a dummy user
        if not User.query.filter_by(username='testuser').first():
            test_user = User(username='testuser', role='user')
            test_user.set_password('test1234')
            db.session.add(test_user)
            db.session.commit()
            print("Created testuser for test.")

        # 2. Run initialization
        print(f"Running ensure_storage_structure with NAS_ROOT={temp_nas_root}")
        ensure_storage_structure(app)

        # 3. Verify results
        expected_dirs = [
            temp_nas_root,
            os.path.join(temp_nas_root, 'users'),
            os.path.join(temp_nas_root, 'shared'),
            os.path.join(temp_nas_root, 'users', 'admin'),
            os.path.join(temp_nas_root, 'users', 'testuser')
        ]

        all_passed = True
        for d in expected_dirs:
            if os.path.exists(d):
                print(f"[OK] Directory exists: {d}")
            else:
                print(f"[FAIL] Directory missing: {d}")
                all_passed = False
        
        if all_passed:
            print("\nSUCCESS: All storage structures are consistent!")
        else:
            print("\nFAILURE: Some storage structures are missing.")

    # Cleanup (Optional: uncomment to remove temp folder after test)
    # shutil.rmtree(temp_nas_root)

if __name__ == '__main__':
    test_startup_consistency()
