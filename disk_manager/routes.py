from flask import render_template, jsonify, request, current_app, flash, redirect, url_for
from . import disk_manager
from .hardware import get_hardware_provider

def get_provider():
    return get_hardware_provider(current_app.config.get('MOCK_HARDWARE', True))

@disk_manager.route('/disks')
def index():
    return render_template('disks.html')

@disk_manager.route('/api/disks')
def list_disks():
    provider = get_provider()
    disks = provider.list_disks()
    raids = provider.list_raid_arrays()
    return jsonify({
        'disks': disks,
        'raids': raids
    })

@disk_manager.route('/api/partition/create', methods=['POST'])
def create_partition():
    data = request.json
    disk_path = data.get('disk_path')
    size_mb = data.get('size_mb')
    fs_type = data.get('fs_type', 'ext4')
    name = data.get('name')
    
    if not disk_path or not size_mb:
        return jsonify({'error': 'Missing parameters'}), 400
        
    provider = get_provider()
    success = provider.create_partition(disk_path, int(size_mb), fs_type, name)
    
    if success:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Failed to create partition'}), 500

@disk_manager.route('/api/partition/delete', methods=['POST'])
def delete_partition():
    data = request.json
    part_path = data.get('part_path')
    
    if not part_path:
        return jsonify({'error': 'Missing parameters'}), 400
        
    provider = get_provider()
    success = provider.delete_partition(part_path)
    
    if success:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Failed to delete partition'}), 500

@disk_manager.route('/api/partition/format', methods=['POST'])
def format_partition():
    data = request.json
    part_path = data.get('part_path')
    fs_type = data.get('fs_type', 'ext4')
    
    if not part_path:
        return jsonify({'error': 'Missing parameters'}), 400
        
    provider = get_provider()
    success = provider.format_partition(part_path, fs_type)
    
    if success:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Failed to format partition'}), 500

@disk_manager.route('/api/raid/create', methods=['POST'])
def create_raid():
    data = request.json
    level = data.get('level')
    devices = data.get('devices') # List of strings
    
    if not level or not devices or len(devices) < 1:
        return jsonify({'error': 'Invalid parameters'}), 400
        
    provider = get_provider()
    success = provider.create_raid_array(str(level), devices)
    
    if success:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Failed to create RAID'}), 500
