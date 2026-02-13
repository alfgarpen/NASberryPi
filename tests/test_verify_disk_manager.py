import sys
import os
import unittest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from disk_manager.hardware import MockHardwareProvider

class TestMockDiskManager(unittest.TestCase):
    def setUp(self):
        self.provider = MockHardwareProvider()
        
    def test_list_disks(self):
        disks = self.provider.list_disks()
        self.assertEqual(len(disks), 3)
        self.assertEqual(disks[0].path, '/dev/sda')
        
    def test_create_partition(self):
        # sdb is empty 2TB
        initial_parts = len(self.provider.get_disk_details('/dev/sdb').partitions)
        self.assertEqual(initial_parts, 0)
        
        success = self.provider.create_partition('/dev/sdb', 500 * 1024, 'ext4', 'sdb1')
        self.assertTrue(success)
        
        updated_disk = self.provider.get_disk_details('/dev/sdb')
        self.assertEqual(len(updated_disk.partitions), 1)
        self.assertEqual(updated_disk.partitions[0].size, 500 * 1024 * 1024 * 1024)
        
    def test_format_partition(self):
        # Create first
        self.provider.create_partition('/dev/sdb', 100 * 1024, 'ext4')
        part_path = '/dev/sdb1' # Mock naming logic
        
        success = self.provider.format_partition(part_path, 'ntfs')
        self.assertTrue(success)
        
        disk = self.provider.get_disk_details('/dev/sdb')
        self.assertEqual(disk.partitions[0].fs_type, 'ntfs')
        
    def test_delete_partition(self):
        self.provider.create_partition('/dev/sdb', 100, 'ext4')
        part_path = '/dev/sdb1'
        
        success = self.provider.delete_partition(part_path)
        self.assertTrue(success)
        self.assertEqual(len(self.provider.get_disk_details('/dev/sdb').partitions), 0)
        
    def test_raid_lifecycle(self):
        # Create mock partitions on separate disks
        self.provider.create_partition('/dev/sdb', 1000, 'ext4') # sdb1
        self.provider.create_partition('/dev/sdc', 1000, 'ext4') # sdc1
        
        devices = ['/dev/sdb1', '/dev/sdc1']
        success = self.provider.create_raid_array('1', devices)
        self.assertTrue(success)
        
        raids = self.provider.list_raid_arrays()
        self.assertEqual(len(raids), 1)
        self.assertEqual(raids[0].level, '1')
        
        # Delete
        success = self.provider.delete_raid_array(raids[0].path)
        self.assertTrue(success)
        self.assertEqual(len(self.provider.list_raid_arrays()), 0)

if __name__ == '__main__':
    unittest.main()
