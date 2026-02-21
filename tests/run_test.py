import sys
import os

# Add the project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from disk_manager.core import get_all_disks
import json

def test_run():
    print("Testing get_all_disks()...")
    disks = get_all_disks()
    out = [d.to_dict() for d in disks]
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    test_run()
