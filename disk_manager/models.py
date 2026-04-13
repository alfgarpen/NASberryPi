from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class PartitionInfo:
    """Represents a partition on a physical disk."""
    name: str  # e.g., 'C:', 'sda1'
    size_bytes: int
    filesystem: str  # e.g., 'NTFS', 'ext4', 'FAT32'
    mount_point: Optional[str] = None

@dataclass
class DiskInfo:
    """Represents a physical disk connected to the system."""
    id: str  # Unique identifier (e.g., node path, device ID)
    name: str  # Human readable name or model
    size_bytes: int
    filesystem: str  # Overall filesystem if applicable, else empty
    mount_points: List[str] = field(default_factory=list)
    is_removable: bool = False
    is_system_disk: bool = False
    partitions: List[PartitionInfo] = field(default_factory=list)

    def to_dict(self):
        """Helper to serialize to a dictionary for the JSON API."""
        return {
            'id': self.id,
            'name': self.name,
            'size_bytes': self.size_bytes,
            'filesystem': self.filesystem,
            'mount_points': self.mount_points,
            'is_removable': self.is_removable,
            'is_system_disk': self.is_system_disk,
            'partitions': [
                {
                    'name': p.name,
                    'size_bytes': p.size_bytes,
                    'filesystem': p.filesystem,
                    'mount_point': p.mount_point
                }
                for p in self.partitions
            ]
        }
