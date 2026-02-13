#!/bin/bash
# =====================================================================
# Deploy Serial-Only Python Files to RND-0003
# Run from your Mac terminal: bash deploy_serial_only.sh
# You will be prompted for the SSH password multiple times.
# =====================================================================

TARGET="cpx003@192.168.40.61"
REMOTE_BASE="/home/cpx003/vst_gm_control_panel/vst_gm_control_panel"
LOCAL_BASE="/Users/dougharty/Documents/Python/vst_gm_control_panel/vst_gm_control_panel"
BACKUP_DIR="_backup_i2c_original_$(date +%Y%m%d_%H%M%S)"

echo "============================================"
echo "  Deploy Serial-Only Build to RND-0003"
echo "============================================"
echo ""
echo "Target: ${TARGET}:${REMOTE_BASE}"
echo "Backup: ${REMOTE_BASE}/${BACKUP_DIR}/"
echo ""

# Step 1: Create backup directory and back up existing files on device
echo "--- Step 1: Backing up current files on device ---"
ssh ${TARGET} "
    mkdir -p ${REMOTE_BASE}/${BACKUP_DIR}
    echo 'Backup directory created: ${BACKUP_DIR}'
    
    # Back up the 4 files we're replacing
    for f in controllers/io_manager.py utils/modem.py utils/alarm_manager.py utils/data_handler.py; do
        if [ -f ${REMOTE_BASE}/\${f} ]; then
            cp ${REMOTE_BASE}/\${f} ${REMOTE_BASE}/${BACKUP_DIR}/\$(basename \${f})
            echo \"  Backed up: \${f}\"
        else
            echo \"  Not found (skip): \${f}\"
        fi
    done
    
    # Also back up pressure_sensor.py since it's no longer imported
    if [ -f ${REMOTE_BASE}/controllers/pressure_sensor.py ]; then
        cp ${REMOTE_BASE}/controllers/pressure_sensor.py ${REMOTE_BASE}/${BACKUP_DIR}/pressure_sensor.py
        echo '  Backed up: controllers/pressure_sensor.py'
    fi
    
    echo 'Backup complete.'
"

if [ $? -ne 0 ]; then
    echo "ERROR: SSH backup step failed. Aborting."
    exit 1
fi

# Step 2: Copy new serial-only files to device
echo ""
echo "--- Step 2: Uploading serial-only files ---"

scp "${LOCAL_BASE}/controllers/io_manager.py" "${TARGET}:${REMOTE_BASE}/controllers/io_manager.py"
echo "  Uploaded: controllers/io_manager.py"

scp "${LOCAL_BASE}/utils/modem.py" "${TARGET}:${REMOTE_BASE}/utils/modem.py"
echo "  Uploaded: utils/modem.py"

scp "${LOCAL_BASE}/utils/alarm_manager.py" "${TARGET}:${REMOTE_BASE}/utils/alarm_manager.py"
echo "  Uploaded: utils/alarm_manager.py"

scp "${LOCAL_BASE}/utils/data_handler.py" "${TARGET}:${REMOTE_BASE}/utils/data_handler.py"
echo "  Uploaded: utils/data_handler.py"

# Step 3: Verify files on device
echo ""
echo "--- Step 3: Verifying deployed files ---"
ssh ${TARGET} "
    echo 'File sizes on device:'
    ls -la ${REMOTE_BASE}/controllers/io_manager.py
    ls -la ${REMOTE_BASE}/utils/modem.py
    ls -la ${REMOTE_BASE}/utils/alarm_manager.py
    ls -la ${REMOTE_BASE}/utils/data_handler.py
    echo ''
    echo 'Backup files:'
    ls -la ${REMOTE_BASE}/${BACKUP_DIR}/
    echo ''
    
    # Check for SERIAL-ONLY marker in io_manager.py header
    if head -15 ${REMOTE_BASE}/controllers/io_manager.py | grep -q 'SERIAL-ONLY'; then
        echo '✓ io_manager.py confirmed as SERIAL-ONLY build'
    else
        echo '✗ WARNING: io_manager.py does NOT contain SERIAL-ONLY marker!'
    fi
"

echo ""
echo "============================================"
echo "  Deployment complete!"
echo "  Backup at: ${REMOTE_BASE}/${BACKUP_DIR}/"
echo ""
echo "  To restart the service:"
echo "    ssh ${TARGET} 'sudo systemctl restart vst_gm_control_panel'"
echo ""
echo "  To rollback:"
echo "    ssh ${TARGET} 'cp ${REMOTE_BASE}/${BACKUP_DIR}/* ${REMOTE_BASE}/controllers/ && cp ${REMOTE_BASE}/${BACKUP_DIR}/modem.py ${REMOTE_BASE}/utils/ && cp ${REMOTE_BASE}/${BACKUP_DIR}/alarm_manager.py ${REMOTE_BASE}/utils/ && cp ${REMOTE_BASE}/${BACKUP_DIR}/data_handler.py ${REMOTE_BASE}/utils/'"
echo "============================================"
