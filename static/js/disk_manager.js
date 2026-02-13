document.addEventListener('DOMContentLoaded', function () {
    loadDisks();

    // Form Event Listeners
    document.getElementById('form-create-part').addEventListener('submit', handleCreatePartition);
    document.getElementById('form-format-part').addEventListener('submit', handleFormatPartition);
    document.getElementById('form-create-raid').addEventListener('submit', handleCreateRaid);
});

function loadDisks() {
    fetch('/api/disks')
        .then(response => response.json())
        .then(data => {
            renderDisks(data.disks);
            renderRaids(data.raids);
            updateRaidCandidateList(data.disks);
        })
        .catch(error => console.error('Error loading disks:', error));
}

function formatBytes(bytes, decimals = 2) {
    if (!+bytes) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function renderDisks(disks) {
    const container = document.getElementById('disk-list');
    container.innerHTML = '';

    if (disks.length === 0) {
        container.innerHTML = '<p>No physical disks found.</p>';
        return;
    }

    disks.forEach(disk => {
        const diskDiv = document.createElement('div');
        diskDiv.className = 'disk-item';
        diskDiv.style.marginBottom = '20px';
        diskDiv.style.padding = '15px';
        diskDiv.style.border = '1px solid #ddd';
        diskDiv.style.borderRadius = '5px';

        // Header
        const header = document.createElement('div');
        header.innerHTML = `<strong>${disk.path}</strong> - ${disk.model} (${formatBytes(disk.size)})`;
        diskDiv.appendChild(header);

        // Partition Bar
        const barContainer = document.createElement('div');
        barContainer.style.display = 'flex';
        barContainer.style.width = '100%';
        barContainer.style.height = '50px';
        barContainer.style.marginTop = '10px';
        barContainer.style.border = '1px solid #999';
        barContainer.style.backgroundColor = '#e0e0e0';

        let currentOffset = 0;

        // Render existing partitions
        disk.partitions.forEach(part => {
            // Calculate gap since last partition (Unallocated)
            // Note: In mock, we don't have start/end sectors, so we just assume packed. 
            // In real app, we'd use part.start_sector.

            const widthPercent = (part.size / disk.size) * 100;
            currentOffset += part.size;

            const partDiv = document.createElement('div');
            partDiv.style.width = `${widthPercent}%`;
            partDiv.style.height = '100%';
            partDiv.style.backgroundColor = getFsColor(part.fs_type);
            partDiv.style.borderRight = '1px solid white';
            partDiv.style.display = 'flex';
            partDiv.style.flexDirection = 'column';
            partDiv.style.justifyContent = 'center';
            partDiv.style.alignItems = 'center';
            partDiv.style.fontSize = '0.8rem';
            partDiv.style.overflow = 'hidden';
            partDiv.style.cursor = 'pointer';
            partDiv.title = `${part.path} (${part.fs_type})`;

            partDiv.innerHTML = `<span>${part.name}</span><span>${formatBytes(part.size)}</span>`;

            // Actions Menu (Simple click handler for now)
            partDiv.onclick = () => showPartitionActions(part);

            barContainer.appendChild(partDiv);
        });

        // Remaining Unallocated
        if (currentOffset < disk.size) {
            const remaining = disk.size - currentOffset;
            const widthPercent = (remaining / disk.size) * 100;

            const unallocDiv = document.createElement('div');
            unallocDiv.style.width = `${widthPercent}%`;
            unallocDiv.style.height = '100%';
            unallocDiv.style.backgroundColor = '#ccc';
            unallocDiv.style.display = 'flex';
            unallocDiv.style.justifyContent = 'center';
            unallocDiv.style.alignItems = 'center';
            unallocDiv.style.cursor = 'pointer';
            unallocDiv.innerHTML = '<small>Unallocated</small>';

            unallocDiv.onclick = () => openCreatePartitionModal(disk.path, remaining);

            barContainer.appendChild(unallocDiv);
        }

        diskDiv.appendChild(barContainer);
        container.appendChild(diskDiv);
    });
}

function getFsColor(fs) {
    if (!fs) return '#6c757d'; // gray
    switch (fs.toLowerCase()) {
        case 'ext4': return '#007bff'; // blue
        case 'ntfs': return '#17a2b8'; // cyan
        case 'fat32': return '#28a745'; // green
        case 'swap': return '#fd7e14'; // orange
        default: return '#6610f2'; // purple
    }
}

function renderRaids(raids) {
    const container = document.getElementById('raid-list');
    container.innerHTML = '';

    if (raids.length === 0) {
        container.innerHTML = '<p>No RAID arrays configured.</p>';
        return;
    }

    // Sort raids by path for consistent ordering
    raids.sort((a, b) => a.path.localeCompare(b.path));

    raids.forEach(raid => {
        const item = document.createElement('div');
        item.className = 'raid-item';
        item.style.borderLeft = '4px solid #007bff';
        item.style.padding = '10px';
        item.style.marginBottom = '10px';
        item.style.backgroundColor = '#f8f9fa';

        item.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong>${raid.path}</strong> - Level: RAID ${raid.level}, Size: ${formatBytes(raid.size)}, State: ${raid.state}
                    <br>
                    <small>Members: ${raid.devices.join(', ')}</small>
                </div>
                <!-- Delete Button -->
                <!-- Ideally confirm before delete -->
            </div>
        `;
        container.appendChild(item);
    });
}


function updateRaidCandidateList(disks) {
    const container = document.getElementById('cr-devices');
    container.innerHTML = '';

    disks.forEach(disk => {
        disk.partitions.forEach(part => {
            // In a real app we'd filter out mounted or busy partitions
            const div = document.createElement('div');
            div.innerHTML = `
                <label>
                    <input type="checkbox" name="raid-device" value="${part.path}">
                    ${part.path} (${formatBytes(part.size)}) - ${disk.model}
                </label>
             `;
            container.appendChild(div);
        });
    });
}

// Modal Actions

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

function openCreatePartitionModal(diskPath, maxBytes) {
    document.getElementById('cp-disk-path').value = diskPath;
    document.getElementById('cp-size').max = Math.floor(maxBytes / (1024 * 1024));
    document.getElementById('cp-size').value = Math.floor(maxBytes / (1024 * 1024));
    document.getElementById('modal-create-part').style.display = 'block';
}

function showPartitionActions(part) {
    // For simplicity, reuse the format modal or create a specific small menu
    // Here we'll just open the Format/Delete option via a simple confirm for now or custom UI?
    // Let's use the Format modal for Format, and a confirm for Delete.
    // Ideally we need a context menu.
    // For MVP: Prompt user choice.

    if (confirm(`Do you want to FORMAT or DELETE ${part.path}?\nOk = Format\nCancel = Delete`)) {
        // Format
        document.getElementById('fp-path').value = part.path;
        document.getElementById('fp-name').textContent = part.path;
        document.getElementById('modal-format-part').style.display = 'block';
    } else {
        // Delete (Check if they actually cancelled or clicked cancel button... tricky with confirm)
        // Better: Use a simple custom UI or just separate buttons in the partition bar?
        // Let's rely on a separate button or click behavior.
        // Re-implementing:
        const action = prompt("Type 'format' to format, 'delete' to delete:");
        if (action === 'format') {
            document.getElementById('fp-path').value = part.path;
            document.getElementById('fp-name').textContent = part.path;
            document.getElementById('modal-format-part').style.display = 'block';
        } else if (action === 'delete') {
            if (confirm(`Are you SURE you want to delete ${part.path}? Data will be lost.`)) {
                deletePartition(part.path);
            }
        }
    }
}

function openCreateRaidModal() {
    document.getElementById('modal-create-raid').style.display = 'block';
}

// API Calls

function handleCreatePartition(e) {
    e.preventDefault();
    const diskPath = document.getElementById('cp-disk-path').value;
    const sizeMb = document.getElementById('cp-size').value;
    const fs = document.getElementById('cp-fs').value;

    fetch('/api/partition/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            disk_path: diskPath,
            size_mb: sizeMb,
            fs_type: fs
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                closeModal('modal-create-part');
                loadDisks();
            } else {
                alert('Error: ' + data.message);
            }
        });
}

function handleFormatPartition(e) {
    e.preventDefault();
    const partPath = document.getElementById('fp-path').value;
    const fs = document.getElementById('fp-fs').value;

    fetch('/api/partition/format', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            part_path: partPath,
            fs_type: fs
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                closeModal('modal-format-part');
                loadDisks();
            } else {
                alert('Error: ' + data.message);
            }
        });
}

function deletePartition(partPath) {
    fetch('/api/partition/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            part_path: partPath
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                loadDisks();
            } else {
                alert('Error: ' + data.message);
            }
        });
}

function handleCreateRaid(e) {
    e.preventDefault();
    const level = document.getElementById('cr-level').value;
    const checkboxes = document.querySelectorAll('input[name="raid-device"]:checked');
    const devices = Array.from(checkboxes).map(cb => cb.value);

    if (devices.length < 1) {
        alert("Please select at least one partition.");
        return;
    }

    fetch('/api/raid/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            level: level,
            devices: devices
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                closeModal('modal-create-raid');
                loadDisks();
            } else {
                alert('Error: ' + data.message);
            }
        });
}
