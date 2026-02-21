from flask import render_template, jsonify, request, current_app, flash, redirect, url_for
from . import disk_manager
from .core import get_all_disks

@disk_manager.route('/disks')
def index():
    return render_template('disks.html')

@disk_manager.route('/api/disks')
def list_disks():
    disks = get_all_disks()
    
    # We serialize DiskInfo objects to dicts
    disks_dict = [d.to_dict() for d in disks]
    
    # RAID is no longer supported in this iteration, returning empty
    return jsonify({
        'disks': disks_dict,
        'raids': []
    })

@disk_manager.route('/api/partition/create', methods=['POST'])
def create_partition():
    return jsonify({'status': 'error', 'message': 'Partition creation is disabled in read-only mode.'}), 403

@disk_manager.route('/api/partition/delete', methods=['POST'])
def delete_partition():
    return jsonify({'status': 'error', 'message': 'Partition deletion is disabled in read-only mode.'}), 403

@disk_manager.route('/api/partition/format', methods=['POST'])
def format_partition():
    return jsonify({'status': 'error', 'message': 'Partition formatting is disabled in read-only mode.'}), 403

@disk_manager.route('/api/raid/create', methods=['POST'])
def create_raid():
    return jsonify({'status': 'error', 'message': 'RAID creation is disabled in read-only mode.'}), 403

