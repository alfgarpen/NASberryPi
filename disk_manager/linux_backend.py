import json
import logging
from typing import List, Optional
from .models import DiskInfo, PartitionInfo
from .utils import run_command

logger = logging.getLogger(__name__)

def parse_linux_disks() -> List[DiskInfo]:
    """
    Uses lsblk to get physical disks and partitions in Linux.
    Returns a list of DiskInfo objects.
    """
    disks = []
    
    # lsblk -J -b -o NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE,RM,ROTA,MODEL,SERIAL
    cmd = [
        "lsblk", 
        "-J",       # JSON output
        "-b",       # Size in bytes
        "-o", "NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE,RM,ROTA,MODEL,SERIAL"
    ]
    
    success, output = run_command(cmd)
    if not success or not output:
        logger.error("Failed to run lsblk or received empty output.")
        return disks
        
    try:
        data = json.loads(output)
        blockdevices = data.get("blockdevices", [])
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse lsblk JSON output: {e}")
        return disks

    for dev in blockdevices:
        # We only want top-level block devices (disks). Skip loop, ram, etc if preferred.
        if dev.get("type") != "disk":
            continue
            
        # Ignore loop devices (snaps, etc)
        name = dev.get("name") or ""
        if name.startswith("loop"):
            continue
            
        disk_id = f"/dev/{name}"
        
        # Handle cases where model is literally null
        raw_model = dev.get("model")
        model = (raw_model.strip() if raw_model else "Unknown Disk") or "Unknown Disk"
        
        size = int(dev.get("size") or 0)
        is_removable = bool(dev.get("rm", False))
        
        disk_fs = dev.get("fstype") or ""
        disk_mp = dev.get("mountpoint") or ""
        
        # Parse children (partitions)
        disk_partitions = []
        overall_fs = ""
        mount_points = []
        is_system = False
        
        if disk_mp:
            mount_points.append(disk_mp)
            overall_fs = disk_fs
            if disk_mp == "/":
                is_system = True
                
        children = dev.get("children") or []
        for child in children:
            if child.get("type") == "part":
                p_name = child.get("name") or ""
                p_size = int(child.get("size") or 0)
                p_fs = child.get("fstype") or "Unknown"
                p_mp = child.get("mountpoint")
                
                part_info = PartitionInfo(
                    name=f"/dev/{p_name}",
                    size_bytes=p_size,
                    filesystem=p_fs,
                    mount_point=p_mp
                )
                disk_partitions.append(part_info)
                
                if p_mp:
                    mount_points.append(p_mp)
                    if p_mp == "/":
                        is_system = True
                
                if not overall_fs and p_fs != "Unknown":
                    overall_fs = p_fs
                    
        disk_info = DiskInfo(
            id=disk_id,
            name=model,
            size_bytes=size,
            filesystem=overall_fs,
            mount_points=mount_points,
            is_removable=is_removable,
            is_system_disk=is_system,
            partitions=disk_partitions
        )
        disks.append(disk_info)

    return disks
