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
        // Extra info badges
        let tags = [];
        if (disk.is_system_disk) tags.push('<span class="badge badge-warning" style="background:#ffc107; color:#000; padding:2px 6px; border-radius:4px; font-size:0.8rem; margin-left:10px;">System</span>');
        if (disk.is_removable) tags.push('<span class="badge badge-info" style="background:#17a2b8; color:#fff; padding:2px 6px; border-radius:4px; font-size:0.8rem; margin-left:10px;">Removable</span>');

        header.innerHTML = `<strong>${disk.name}</strong> - ${formatBytes(disk.size_bytes)} ${tags.join('')}`;
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
        if (disk.partitions && disk.partitions.length > 0) {
            disk.partitions.forEach(part => {
                const widthPercent = (part.size_bytes / disk.size_bytes) * 100;
                currentOffset += part.size_bytes;

                const partDiv = document.createElement('div');
                partDiv.style.width = Math.max(widthPercent, 1) + '%'; // Ensure at least 1% so it's visible
                partDiv.style.height = '100%';
                partDiv.style.backgroundColor = getFsColor(part.filesystem);
                partDiv.style.borderRight = '1px solid white';
                partDiv.style.display = 'flex';
                partDiv.style.flexDirection = 'column';
                partDiv.style.justifyContent = 'center';
                partDiv.style.alignItems = 'center';
                partDiv.style.fontSize = '0.8rem';
                partDiv.style.overflow = 'hidden';
                partDiv.style.cursor = 'default'; // Read-only

                let title = `${part.name} (${part.filesystem})`;
                if (part.mount_point) title += ` Mounted at: ${part.mount_point}`;
                partDiv.title = title;

                partDiv.innerHTML = `<span>${part.name}</span><span>${formatBytes(part.size_bytes)}</span>`;
                barContainer.appendChild(partDiv);
            });
        }

        // Remaining Unallocated
        if (currentOffset < disk.size_bytes && disk.size_bytes > 0) {
            const remaining = disk.size_bytes - currentOffset;
            const widthPercent = (remaining / disk.size_bytes) * 100;

            // Only show unallocated block if it is larger than 50MB
            // Windows reserves small sectors for alignment / EFI / metadata
            if (remaining > (50 * 1024 * 1024)) {
                const unallocDiv = document.createElement('div');
                unallocDiv.style.width = `${widthPercent}%`;
                unallocDiv.style.height = '100%';
                unallocDiv.style.backgroundColor = '#ccc';
                unallocDiv.style.display = 'flex';
                unallocDiv.style.justifyContent = 'center';
                unallocDiv.style.alignItems = 'center';
                unallocDiv.style.cursor = 'default'; // Read-only
                unallocDiv.innerHTML = `<small>Free (${formatBytes(remaining)})</small>`;
                barContainer.appendChild(unallocDiv);
            }
        }

        diskDiv.appendChild(barContainer);
        container.appendChild(diskDiv);
    });
}

function getFsColor(fs) {
    if (!fs || fs === 'Unknown') return '#6c757d'; // gray
    switch (fs.toLowerCase()) {
        case 'ext4': return '#007bff'; // blue
        case 'ntfs': return '#17a2b8'; // cyan
        case 'fat32': return '#28a745'; // green
        case 'vfat': return '#28a745';
        case 'swap': return '#fd7e14'; // orange
        default: return '#6610f2'; // purple
    }
}

function renderRaids(raids) {
    const container = document.getElementById('raid-list');
    container.innerHTML = '<p>RAID management is read-only and currently disabled in this deployment.</p>';
}

function updateRaidCandidateList(disks) {
    const container = document.getElementById('cr-devices');
    container.innerHTML = '<p>RAID creation is disabled.</p>';
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

function openCreateRaidModal() {
    alert("RAID creation is disabled in read-only mode.");
}

// Dummy handler to prevent errors if elements remain
function handleCreatePartition(e) {
    e.preventDefault();
    alert("Disabled");
}

function handleFormatPartition(e) {
    e.preventDefault();
    alert("Disabled");
}

function handleCreateRaid(e) {
    e.preventDefault();
    alert("Disabled");
}
