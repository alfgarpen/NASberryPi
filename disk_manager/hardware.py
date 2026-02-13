import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import random

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class Partition:
    path: str
    size: int  # bytes
    fs_type: str  # ext4, ntfs, etc.
    mount_point: Optional[str] = None
    name: str = "" # e.g. sda1

@dataclass
class Disk:
    path: str  # e.g. /dev/sda
    model: str
    size: int  # bytes
    partitions: List[Partition] = field(default_factory=list)
    rotational: bool = True  # True=HDD, False=SSD
    serial: str = ""

@dataclass
class RaidArray:
    path: str # e.g. /dev/md0
    level: str # raid0, raid1, raid5
    size: int
    state: str # clean, active, degraded
    devices: List[str] # list of partition paths e.g. /dev/sdb1

class HardwareProvider:
    """Abstract base class for disk operations."""
    def list_disks(self) -> List[Disk]:
        raise NotImplementedError
    
    def get_disk_details(self, path: str) -> Optional[Disk]:
        raise NotImplementedError

    def create_partition(self, disk_path: str, size_mb: int, fs_type: str, name: Optional[str] = None) -> bool:
        raise NotImplementedError

    def delete_partition(self, part_path: str) -> bool:
        raise NotImplementedError

    def format_partition(self, part_path: str, fs_type: str) -> bool:
        raise NotImplementedError
        
    def list_raid_arrays(self) -> List[RaidArray]:
        raise NotImplementedError
        
    def create_raid_array(self, level: str, devices: List[str]) -> bool:
        raise NotImplementedError
        
    def delete_raid_array(self, raid_path: str) -> bool:
        raise NotImplementedError
        
    def refresh(self):
        """Force refresh of hardware state (useful for real hardware)"""
        pass

class MockHardwareProvider(HardwareProvider):
    """In-memory simulation of disks and RAID."""
    
    def __init__(self):
        self.disks: Dict[str, Disk] = {}
        self.raid_arrays: Dict[str, RaidArray] = {}
        self._init_mock_data()
        
    def _init_mock_data(self):
        # 1TB HDD with OS partition and Data partition
        sda = Disk(path='/dev/sda', model='WDC WD10EZEX', size=1000 * 1024**3, serial="WD-1234")
        sda.partitions.append(Partition(path='/dev/sda1', size=512 * 1024**2, fs_type='fat32', mount_point='/boot/firmware', name='sda1'))
        sda.partitions.append(Partition(path='/dev/sda2', size=64 * 1024**3, fs_type='ext4', mount_point='/', name='sda2'))
        # Determine remaining space? For mock, we just track partitions.
        self.disks['/dev/sda'] = sda
        
        # 2TB HDD (Empty)
        sdb = Disk(path='/dev/sdb', model='Seagate Barracuda', size=2000 * 1024**3, serial="ST-5678")
        self.disks['/dev/sdb'] = sdb
        
        # 2TB HDD (Empty)
        sdc = Disk(path='/dev/sdc', model='Seagate Barracuda', size=2000 * 1024**3, serial="ST-9012")
        self.disks['/dev/sdc'] = sdc

    def list_disks(self) -> List[Disk]:
        return list(self.disks.values())

    def get_disk_details(self, path: str) -> Optional[Disk]:
        return self.disks.get(path)

    def create_partition(self, disk_path: str, size_mb: int, fs_type: str, name: Optional[str] = None) -> bool:
        disk = self.disks.get(disk_path)
        if not disk:
            logger.error(f"Disk {disk_path} not found")
            return False
            
        # Simplified Mock Logic: Just append a new partition
        # In real life, we'd check free space gaps.
        
        part_num = len(disk.partitions) + 1
        part_name = f"{disk_path.split('/')[-1]}{part_num}"
        part_path = f"{disk_path}{part_num}"
        
        # Mock check: Sum of parts vs total
        used = sum(p.size for p in disk.partitions)
        requested = size_mb * 1024**2
        if used + requested > disk.size:
             logger.error("Not enough space")
             return False
             
        new_part = Partition(
            path=part_path,
            size=requested,
            fs_type=fs_type,
            name=name or part_name
        )
        disk.partitions.append(new_part)
        logger.info(f"Created mocked partition {part_path} ({size_mb} MB, {fs_type})")
        return True

    def delete_partition(self, part_path: str) -> bool:
        # Find which disk contains this partition
        for disk in self.disks.values():
            for i, p in enumerate(disk.partitions):
                if p.path == part_path:
                    disk.partitions.pop(i)
                    logger.info(f"Deleted mocked partition {part_path}")
                    return True
        return False

    def format_partition(self, part_path: str, fs_type: str) -> bool:
        for disk in self.disks.values():
            for p in disk.partitions:
                if p.path == part_path:
                    p.fs_type = fs_type
                    logger.info(f"Formatted mocked {part_path} to {fs_type}")
                    return True
        return False
        
    def list_raid_arrays(self) -> List[RaidArray]:
        return list(self.raid_arrays.values())
        
    def create_raid_array(self, level: str, devices: List[str]) -> bool:
        # Mock: Create a new md device
        md_id = len(self.raid_arrays)
        md_path = f"/dev/md{md_id}"
        
        # Calculate size (Simplified)
        total_size = 0
        min_size = float('inf')
        
        # Verify devices exist
        # note: devices are partition paths e.g. /dev/sdb1
        # In mock, we assume they are valid if passed from UI selectors ideally
        
        # Simple size calc
        for d in devices:
             # Find partition size
             pass # assume standard 
             min_size = 1000 * 1024**3 # Mock placeholders
             
        if level == '0':
            size = min_size * len(devices)
        elif level == '1':
            size = min_size
        else:
            size = min_size * (len(devices) - 1) # simple Raid 5 calc
            
        new_raid = RaidArray(
            path=md_path,
            level=level,
            size=int(size),
            state='clean',
            devices=devices
        )
        self.raid_arrays[md_path] = new_raid
        logger.info(f"Created mocked RAID {md_path} level {level}")
        return True
        
    def delete_raid_array(self, raid_path: str) -> bool:
        if raid_path in self.raid_arrays:
            del self.raid_arrays[raid_path]
            return True
        return False

class RealHardwareProvider(HardwareProvider):
    # Placeholder for real implementation
    pass

# Singleton instance
_provider = None

def get_hardware_provider(mock_mode: bool) -> HardwareProvider:
    global _provider
    if _provider:
        return _provider
        
    if mock_mode:
        _provider = MockHardwareProvider()
    else:
        _provider = RealHardwareProvider()
    
    return _provider
