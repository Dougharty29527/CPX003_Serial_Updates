'''
Data handler module
'''

# Standard imports.
import csv
from datetime import datetime
import grp
import os
from pathlib import Path
import pwd
import signal
import stat
import subprocess
import threading
from zoneinfo import ZoneInfo

# Kivy imports.
from kivymd.app import MDApp
from kivy.logger import Logger


class DataHandler:
    '''
    Class to handle data logging.
    '''

    def __init__(self, file_path='/media/cpx003'):
        self.app = MDApp.get_running_app()
        self.base_path = Path(file_path)
        self.file_name = 'logfile.csv'
        self.headers = [
            'Device',
            'UST Pressure',
            'Run Cycles',
            'Run Mode',
            'Faults (Alarms)',
            'Motor Amps',
            'Date (Local)',
            'Time (Local)',
            'Date (UTC)',
            'Time (UTC)',
        ]
        # Try to find or create external file, with graceful fallback
        self.file_path = self.find_or_create_external_file()
        
        # If external file creation failed, create a local fallback
        if self.file_path is None:
            self.file_path = self.create_local_fallback()

    def find_or_create_external_file(self):
        '''
        Look for logfile.csv in the root of directories inside external file path.
        If not found, create it in the first available directory with specified headers.
        Handles permission errors gracefully.
        '''
        try:
            if self.base_path.exists() and self.base_path.is_dir():
                for directory in self.base_path.iterdir():
                    if directory.is_dir():
                        # Try to fix directory permissions first
                        try:
                            os.chmod(directory, 0o755)
                        except PermissionError:
                            # If we can't fix directory permissions, try anyway
                            pass
                        except Exception:
                            # Other errors, continue trying
                            pass
                            
                        file_path = directory / self.file_name
                        try:
                            if file_path.exists():
                                if self.verify_headers(file_path):
                                    self.ensure_permissions(file_path)
                                    return file_path
                                else:
                                    self.rename_log_file(file_path)
                            created_path = self.create_log_file(file_path)
                            if created_path:
                                return created_path
                        except PermissionError as e:
                            continue  # Try next directory
                        except Exception as e:
                            continue  # Try next directory
        except PermissionError as e:
            pass
        except Exception as e:
            pass
        return None

    def verify_headers(self, file_path):
        '''
        Verify if the headers in the existing file match the expected headers.
        '''
        try:
            with file_path.open('r', newline='') as log_file:
                reader = csv.reader(log_file)
                existing_headers = next(reader)
                return existing_headers == self.headers
        except Exception as e:
            return False

    def rename_log_file(self, file_path):
        '''
        Rename the existing log file with a datetime suffix.
        '''
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        new_file_path = file_path.with_name(f'{file_path.stem}_{timestamp}{file_path.suffix}')
        try:
            file_path.rename(new_file_path)
        except Exception as e:
            pass

    def create_log_file(self, file_path):
        '''
        Create a log file with headers.
        '''
        try:
            with file_path.open('w', newline='') as log_file:
                writer = csv.writer(log_file)
                writer.writerow(self.headers)
            self.ensure_permissions(file_path)
            return file_path
        except Exception as e:
            return None

    def ensure_permissions(self, file_path):
        '''
        Ensure that the logfile has the correct permissions and ownership.
        '''
        try:
            # Set file permissions to 775 (read/write/execute for owner and group, read/execute for others)
            os.chmod(file_path, 0o775)
            
            # Try to set ownership to cpx003:cpx003 if we have the privileges
            try:
                import pwd
                import grp
                uid = pwd.getpwnam('cpx003').pw_uid
                gid = grp.getgrnam('cpx003').gr_gid
                os.chown(file_path, uid, gid)
            except (KeyError, PermissionError) as e:
                # If we can't change ownership, that's okay - just log it
                pass

        except PermissionError as e:
            pass
        except Exception as e:
            pass

    def create_local_fallback(self):
        '''
        Create a local fallback log file when external storage is not accessible.
        '''
        try:
            # Create a local logs directory in the application directory
            local_logs_dir = Path('/home/cpx003/vst_gm_control_panel/logs')
            local_logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure the directory has proper permissions
            try:
                os.chmod(local_logs_dir, 0o775)
            except Exception as e:
                pass
            
            local_file_path = local_logs_dir / self.file_name
            
            # If file exists, verify headers
            if local_file_path.exists():
                if self.verify_headers(local_file_path):
                    self.ensure_permissions(local_file_path)
                    return local_file_path
                else:
                    # Rename existing file with incorrect headers
                    self.rename_log_file(local_file_path)
            
            # Create new log file
            created_path = self.create_log_file(local_file_path)
            if created_path:
                return created_path
            else:
                return None
                
        except Exception as e:
            return None

    def _attempt_file_recovery(self):
        '''
        Attempt to recover from file access issues by trying external path first,
        then falling back to local storage.
        '''
        try:
            # First try to recreate external file
            self.file_path = self.find_or_create_external_file()
            
            # If external fails, use local fallback
            if self.file_path is None:
                self.file_path = self.create_local_fallback()
                
            if self.file_path is None:
                pass
        except Exception as e:
            pass

    def get_current_datetime(self):
        '''
        Get the current date and time formatted as MM/DD/YYYY and HH:MM:SS TZ.
        '''
        now_local = datetime.now()
        local_time = now_local.strftime('%H:%M:%S')
        # Separating time and date locale for manual time entry functionality.
        timezone_map = {'ES': 'Europe/Madrid', 'EN': 'America/New_York'}
        current_date = datetime.now(ZoneInfo(timezone_map.get(self.app.language, 'UTC')))
        self.app.set_locale()
        local_date = current_date.strftime('%m/%d/%Y')
        local_time_zone = current_date.strftime('%Z')
        date_local = f'{local_date} {local_time_zone}'
        time_local = f'{local_time} {local_time_zone}'
        # Getting UTC date and time
        now_utc = datetime.now(ZoneInfo('UTC'))
        date_utc = now_utc.strftime('%m/%d/%Y %Z')
        time_utc = now_utc.strftime('%H:%M:%S %Z')
        datetime_utc = now_utc.strftime('%m/%d/%Y %H:%M:%S %Z')
        return date_local, time_local, date_utc, time_utc

    def get_current_mode(self):
        '''
        Get the current GM mode using ultra-fast memory-mapped file (replaces database).
        
        REV 10 PATCH: Added bleed (8) and leak (9) mappings to match ESP32
        setRelaysForMode() numbering. Previously these modes were unmapped
        and would default to 0 (rest), causing incorrect relay states during
        bleed/leak test operations sent to ESP32.
        '''
        # REV 10 PATCH: Complete mode map matching ESP32 setRelaysForMode() numbers
        MODE_MAP = {
            'rest': 0, 'run': 1, 'purge': 2, 'burp': 3,
            'bleed': 8, 'leak': 9
        }
        current_mode = self.app.io.mode_manager.get_mode()
        return MODE_MAP.get(current_mode, 0)

    def get_current_alarms(self):
        '''
        Get and decode any active alarms.
        '''
        # Mapping alarm names to their corresponding numbers
        alarm_map = {
            'vac_pump': 1,
            'panel_power': 2,
            'overfill': 4,
            'digital_storage': 8,
            'under_pressure': 16,
            'over_pressure': 32,
            'zero_pressure': 64,
            'variable_pressure': 128,
            'pressure_sensor': 256,
            '72_hour_shutdown': 512
        }

        active_alarms = self.app.get_active_alarm_names()
        active_alarm_numbers = [number for name, number in alarm_map.items() if name in active_alarms]

        # Calculate the sum of active alarm numbers
        total_active_alarms = sum(active_alarm_numbers)

        return total_active_alarms

    def write_log_entry(self, *args):
        '''
        Write an entry to the log file with USB resilience.
        '''
        device = self.app.device_name
        pressure = self.app.current_pressure
        ust_pressure = '0.00'

        if pressure:
            try:
                ust_pressure = str(pressure)
            except ValueError:
                ust_pressure = '0.00'

        run_cycles = self.app.current_run_cycle_count
        run_mode = self.get_current_mode()
        faults = self.get_current_alarms()

        amps = self.app.current_amps
        motor_amps = '0.00'
    
        if amps:
            try:
                motor_amps = str(amps)
            except ValueError:
                motor_amps = '0.00'

        date_local, time_local, date_utc, time_utc = self.get_current_datetime()

        # Prepare log entry data
        log_entry = [
            device,
            ust_pressure,
            run_cycles,
            run_mode,
            faults,
            motor_amps,
            date_local,
            time_local,
            date_utc,
            time_utc
        ]

        # Try to write with USB resilience
        if self.file_path:
            success = self._write_log_entry_safe(log_entry)
            if not success:
                # If write failed, attempt recovery and try local fallback
                self._attempt_file_recovery()
                if self.file_path:
                    self._write_log_entry_safe(log_entry)
        else:
            self._attempt_file_recovery()
            if self.file_path:
                self._write_log_entry_safe(log_entry)

    def _write_log_entry_safe(self, log_entry):
        '''
        Safely write log entry with timeout protection against USB blocking.
        Returns True if successful, False otherwise.
        '''
        if not self.file_path:
            return False

        # For USB paths, check accessibility first but don't be too aggressive
        if str(self.file_path).startswith('/media/'):
            # Try a quick accessibility check, but don't fail immediately
            if not self._is_usb_accessible_safe():
                # USB might not be accessible, but try writing anyway first
                # If it fails, then fall back to local
                success = self._write_to_file_with_timeout(self.file_path, log_entry, timeout=2)
                if not success:
                    return self._write_to_local_fallback(log_entry)
                return success

        # Try to write with timeout protection
        return self._write_to_file_with_timeout(self.file_path, log_entry)

    def _is_usb_accessible_safe(self):
        '''
        Safely check if USB storage is accessible - USB crash fix.
        '''
        try:
            # Add small delay to avoid checking during active USB mounting/unmounting
            import time
            time.sleep(0.02)
            
            # Check if the actual file path exists and is writable
            if self.file_path and self.file_path.exists():
                # Try to check if the parent directory is accessible
                parent_dir = self.file_path.parent
                if parent_dir.exists() and os.access(parent_dir, os.W_OK):
                    return True
            
            # Simple directory content check - avoid subprocess calls during USB events
            try:
                if Path('/media/cpx003').exists():
                    # Check if there are any subdirectories (mounted USB drives)
                    subdirs = [d for d in Path('/media/cpx003').iterdir() if d.is_dir()]
                    return len(subdirs) > 0
                return False
            except (OSError, PermissionError):
                # Directory might be busy during USB mounting/unmounting
                return False
        except Exception:
            # Any error during USB activity - assume not accessible
            return False

    def _write_to_file_with_timeout(self, file_path, log_entry, timeout=3):
        '''
        Write to file with timeout protection using threading.
        '''
        result = {'success': False, 'error': None}
        
        def write_worker():
            try:
                with file_path.open('a', newline='') as log_file:
                    writer = csv.writer(log_file)
                    writer.writerow(log_entry)
                result['success'] = True
            except Exception as e:
                result['error'] = e

        # Use thread with timeout
        thread = threading.Thread(target=write_worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            # Thread is still running - operation timed out
            return False
        elif result['success']:
            return True
        else:
            # Handle specific errors
            error = result['error']
            if isinstance(error, FileNotFoundError):
                pass
            elif isinstance(error, PermissionError):
                pass
            else:
                pass
            return False

    def _write_to_local_fallback(self, log_entry):
        '''
        Write log entry to local fallback location when USB is unavailable.
        '''
        try:
            # Create local fallback if it doesn't exist
            local_fallback_path = self.create_local_fallback()
            if local_fallback_path:
                # Temporarily switch to local path
                original_path = self.file_path
                self.file_path = local_fallback_path
                
                # Try to write to local fallback with timeout
                success = self._write_to_file_with_timeout(local_fallback_path, log_entry, timeout=2)
                
                if success:
                    # Keep using local fallback for now
                    return True
                else:
                    # Restore original path if local write failed
                    self.file_path = original_path
                    return False
            else:
                return False
        except Exception as e:
            return False