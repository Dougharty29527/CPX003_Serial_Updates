# Utilities Module Documentation

This directory contains utility modules that provide common functionality used across the VST Green Machine Control Panel application.

## Contents

- [AlarmManager](#alarmmanager)
- [DatabaseManager](#databasemanager)
- [System Optimization](#system-optimization)
- [Other Utilities](#other-utilities)

## AlarmManager

[Previous AlarmManager documentation remains unchanged...]

## DatabaseManager

[Previous DatabaseManager documentation remains unchanged...]

## System Optimization

The `stabilize_pi.py` module provides automated system optimization and maintenance for the Raspberry Pi platform. This utility runs daily as part of the application's maintenance cycle.

### Key Features

1. **Cache Management**
   - Cleans user caches (pip, poetry, cursor)
   - Prunes old VS Code Server builds
   - Maintains system efficiency by removing unnecessary files

2. **System Log Management**
   - Vacuums systemd journals
   - Retains logs for 3 days
   - Prevents log files from consuming excessive storage

3. **Package Management**
   - Weekly check for required packages
   - Ensures dphys-swapfile and earlyoom are installed
   - Uses timestamp tracking to minimize unnecessary updates

4. **Swap Configuration**
   - Manages swap size (CONF_SWAPSIZE=4096, CONF_MAXSWAP=8192)
   - Smart swap rebuilding (only when needed)
   - Ensures swap is always active

5. **System Tuning**
   - Sets vm.swappiness=60
   - Enables earlyoom service
   - Optimizes memory management

### Integration

The script is integrated into the main application's maintenance cycle through the hourly_updates method:

```python
def run_stabilize_pi(self):
    '''Run the stabilize_pi script if 24 hours have elapsed since last run.'''
    try:
        last_run = self.gm_db.get_setting('last_stabilize_run')
        current_time = datetime.now()
        
        if last_run is None or (current_time - datetime.fromisoformat(last_run)) >= timedelta(days=1):
            result = subprocess.run(['sudo', '-E', 'python3', 'utils/stabilize_pi.py'], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                self.gm_db.add_setting('last_stabilize_run', current_time.isoformat())
                self.sys_notifs.add_notification(
                    current_time.isoformat(),
                    'System optimization completed successfully'
                )
            else:
                self.sys_notifs.add_notification(
                    current_time.isoformat(),
                    f'System optimization failed: {result.stderr}'
                )
```

### Error Handling

The script implements comprehensive error handling:
- Each operation is isolated in its own try-except block
- Non-critical failures don't stop subsequent operations
- All errors are logged for troubleshooting
- Proper cleanup on any failure

### Execution Requirements

- Requires root privileges (handled automatically via sudo)
- Runs as a daily maintenance task
- Tracks last execution time in the database
- Uses atomic operations for file modifications

### Configuration

The script uses several configurable parameters:

```python
DEFAULT_SWAP_SIZE_MB = 4096
MAX_SWAP_SIZE_MB = 8192
JOURNAL_RETENTION_DAYS = '3d'
SWAPPINESS_VALUE = 60
```

These values can be adjusted based on system requirements.

## Other Utilities

[Previous Other Utilities documentation remains unchanged...]