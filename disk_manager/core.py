import platform
import logging
from typing import List, Optional
from .models import DiskInfo

logger = logging.getLogger(__name__)

# Determine the OS and load the appropriate backend
OS_TYPE = platform.system()

if OS_TYPE == "Windows":
    from .windows_backend import parse_windows_disks as get_disks_backend
elif OS_TYPE == "Linux":
    from .linux_backend import parse_linux_disks as get_disks_backend
else:
    logger.warning(f"Unsupported OS: {OS_TYPE}. Disk management features will be limited or unavailable.")
    def get_disks_backend() -> List[DiskInfo]:
        return []

def get_all_disks() -> List[DiskInfo]:
    """
    Returns a list of all physical disks detected on the system.
    """
    try:
        return get_disks_backend()
    except Exception as e:
        logger.error(f"Error fetching disks: {e}")
        return []

def get_disk_by_id(disk_id: str) -> Optional[DiskInfo]:
    """
    Returns a specific physical disk by its ID, or None if not found.
    """
    disks = get_all_disks()
    for d in disks:
        if str(d.id) == str(disk_id):
            return d
    return None

def refresh_disks():
    """
    Placeholder for triggering a forced hardware rescan.
    Usually unnecessary as API calls fetch real-time data, but may be useful in Linux (e.g. partprobe).
    """
    logger.info("refresh_disks called. Disk detection is inherently real-time.")
    pass
