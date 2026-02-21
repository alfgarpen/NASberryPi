import json
import logging
from typing import List, Optional
from .models import DiskInfo, PartitionInfo
from .utils import run_command

logger = logging.getLogger(__name__)

def parse_windows_disks() -> List[DiskInfo]:
    """
    Uses PowerShell to get physical disks, partitions, and volumes in Windows.
    Returns a list of DiskInfo objects.
    """
    disks = []
    
    # 1. Get Physical Disks
    # PowerShell command to get disk info in JSON format
    disk_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, Size, MediaType, BusType | ConvertTo-Json -Compress"
    ]
    
    success, disk_output = run_command(disk_cmd)
    if not success or not disk_output:
        logger.error("Failed to get physical disks from Windows PowerShell.")
        return disks

    try:
        # PowerShell single object might not be an array, ensure it is
        raw_disks = json.loads(disk_output)
        if not isinstance(raw_disks, list):
            raw_disks = [raw_disks]
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse disk JSON output: {e}")
        return disks

    # 2. Get Partitions and Volumes mapping
    # We use Get-Partition and Get-Volume to map drives to physical disks
    part_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-Partition | Select-Object DiskNumber, PartitionNumber, DriveLetter, Size | ConvertTo-Json -Compress"
    ]
    
    success, part_output = run_command(part_cmd)
    partitions_by_disk = {}
    if success and part_output:
        try:
            raw_parts = json.loads(part_output)
            if not isinstance(raw_parts, list):
                raw_parts = [raw_parts]
                
            for p in raw_parts:
                d_num = str(p.get("DiskNumber"))
                if d_num not in partitions_by_disk:
                    partitions_by_disk[d_num] = []
                partitions_by_disk[d_num].append(p)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse partition JSON output: {e}")

    vol_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-Volume | Select-Object DriveLetter, FileSystem, DriveType | ConvertTo-Json -Compress"
    ]
    
    success, vol_output = run_command(vol_cmd)
    volumes_by_letter = {}
    if success and vol_output:
        try:
            raw_vols = json.loads(vol_output)
            if not isinstance(raw_vols, list):
                raw_vols = [raw_vols]
                
            for v in raw_vols:
                letter = v.get("DriveLetter")
                if letter:
                    # DriveLetter might be a char integer if empty? PowerShell JSON sometimes does weird things
                    if isinstance(letter, int):
                        letter = chr(letter)
                    volumes_by_letter[str(letter)] = v
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse volume JSON output: {e}")

    # Build DiskInfo models
    for d in raw_disks:
        disk_id = str(d.get("DeviceId", ""))
        name = d.get("FriendlyName", "Unknown Disk")
        size = d.get("Size", 0)
        bus_type = d.get("BusType", "")
        media_type = d.get("MediaType", "")
        
        is_removable = (bus_type == "USB")
        
        # Resolve Partitions
        disk_partitions = []
        overall_fs = ""
        mount_points = []
        is_system = False
        
        parts = partitions_by_disk.get(disk_id, [])
        for p in parts:
            letter = p.get("DriveLetter")
            if isinstance(letter, int) and letter > 0:
                 letter = chr(letter)
            
            p_size = int(p.get("Size", 0))
            
            p_name = f"Partition {p.get('PartitionNumber', '?')}"
            fs_type = "Unknown"
            mp = None
            
            if letter and isinstance(letter, str) and letter.isalpha():
                p_name = f"{letter}:\\"
                mp = f"{letter}:\\"
                mount_points.append(mp)
                
                # Check volume for filesystem
                vol = volumes_by_letter.get(letter, {})
                fs_type = vol.get("FileSystem", "Unknown") or "Unknown"
                
                # Naive system disk check (usually C:)
                if letter.upper() == 'C':
                    is_system = True
                
                if not overall_fs:
                    overall_fs = fs_type
            
            # Appending all partitions even those without drive letters 
            # (e.g., Hidden EFI System Partitions, Recovery Partitions)
            part_info = PartitionInfo(
                name=p_name,
                size_bytes=p_size,
                filesystem=fs_type,
                mount_point=mp
            )
            disk_partitions.append(part_info)
            
        disk_info = DiskInfo(
            id=disk_id,
            name=f"{name} ({media_type})".strip(" ()"),
            size_bytes=size,
            filesystem=overall_fs,
            mount_points=mount_points,
            is_removable=is_removable,
            is_system_disk=is_system,
            partitions=disk_partitions
        )
        disks.append(disk_info)

    return disks
