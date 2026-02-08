'''
Alarm Manager for VST Green Machine Control Panel.
'''

# Standard imports
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import errno
import logging
import os
import shutil
import threading
import time
from typing import Dict, List, Optional, Set, Callable, Any, Union

# Kivy imports
from kivymd.app import MDApp
from kivy.logger import Logger


class AlarmCondition(ABC):
    """
    Abstract base class for alarm condition strategies.
    
    This class defines the interface for alarm condition checking, allowing
    different alarm types to implement their own specific condition logic.
    """
    
    @abstractmethod
    def check(self, context: 'Alarm') -> bool:
        """
        Check if the alarm condition is currently met.
        
        Args:
            context: The Alarm object which provides access to system state
            
        Returns:
            True if the alarm condition is met, False otherwise
        """
        pass
    
    def _get_pressure(self, context: 'Alarm') -> float:
        """
        Get the current pressure reading from the system.
        
        Args:
            context: The Alarm object which provides access to system state
            
        Returns:
            The current pressure as a float, or -99.9 if unavailable
        """
        pressure_value = context.app.current_pressure
        pressure = -99.9  # Default value for pressure
        
        if pressure_value:
            try:
                # Extract numeric value from pressure string (e.g., '1.5 inHg')
                if isinstance(pressure_value, str) and ' ' in pressure_value:
                    pressure = pressure_value.split()[0]
                else:
                    pressure = pressure_value
                pressure = float(pressure)
            except ValueError:
                Logger.debug('AlarmCondition: Could not parse pressure value')
        return pressure


class AlarmRepository:
    """
    Repository for alarm state persistence.
    
    This class centralizes all database operations related to alarms,
    providing a clean interface for persistence operations.
    """
    
    def __init__(self):
        """Initialize the alarm repository."""
        self.app = MDApp.get_running_app()
    
    def get_start_time(self, alarm_name: str) -> Optional[datetime]:
        """
        Get the start time of an alarm from the database.
        
        Args:
            alarm_name: The name of the alarm
            
        Returns:
            The start time as a datetime object, or None if not found
        """
        try:
            start_time = self.app.alarms_db.get_setting(f'{alarm_name}_start_time')
            return datetime.fromisoformat(start_time) if start_time else None
        except Exception as e:
            Logger.error(f'AlarmManager: Error getting start time for {alarm_name}: {e}')
            return None
    
    def save_start_time(self, alarm_name: str, start_time: datetime) -> None:
        """
        Save the start time of an alarm to the database.
        
        Args:
            alarm_name: The name of the alarm
            start_time: The start time to save
        """
        try:
            self.app.alarms_db.add_setting(f'{alarm_name}_start_time', start_time.isoformat())
            self.app.gm_db.add_setting(f'{alarm_name}_alarm', True)
        except Exception as e:
            Logger.error(f'AlarmManager: Error saving start time for {alarm_name}: {e}')
    
    def clear_start_time(self, alarm_name: str) -> None:
        """
        Clear the start time of an alarm in the database.
        
        Args:
            alarm_name: The name of the alarm
        """
        try:
            self.app.alarms_db.add_setting(f'{alarm_name}_start_time', None)
            self.app.gm_db.add_setting(f'{alarm_name}_alarm', False)
        except Exception as e:
            Logger.error(f'AlarmManager: Error clearing start time for {alarm_name}: {e}')
    
    def get_threshold(self, setting_name: str, default_value: Any) -> Any:
        """
        Get a threshold value from the database.
        
        Args:
            setting_name: The name of the threshold setting
            default_value: Default value to use if not found
            
        Returns:
            The threshold value
        """
        try:
            threshold = self.app.thresholds_db.get_setting(setting_name)
            if threshold is None:
                try:
                    self.app.thresholds_db.add_setting(setting_name, default_value)
                except Exception:
                    # If we can't save the default, just return it anyway
                    pass
                return default_value
            return threshold
        except Exception as e:
            Logger.error(f'AlarmManager: Error getting threshold {setting_name}: {e}')
            return default_value
    
    def get_last_overfill_time(self) -> Optional[datetime]:
        """
        Get the last time an overfill condition was detected.
        
        Returns:
            The last overfill time as a datetime, or None if not found
        """
        try:
            overfill_time = self.app.alarms_db.get_setting('last_overfill_time', None)
            return datetime.fromisoformat(overfill_time) if overfill_time else None
        except Exception as e:
            Logger.error(f'AlarmManager: Error getting last overfill time: {e}')
            return None
    
    def save_last_overfill_time(self, time: datetime) -> None:
        """
        Save the last time an overfill condition was detected.
        
        Args:
            time: The time to save
        """
        try:
            self.app.alarms_db.add_setting('last_overfill_time', time.isoformat())
        except Exception as e:
            Logger.error(f'AlarmManager: Error saving last overfill time: {e}')
    
    def clear_last_overfill_time(self) -> None:
        """Clear the last overfill time from the database."""
        try:
            self.app.alarms_db.add_setting('last_overfill_time', None)
        except Exception as e:
            Logger.error(f'AlarmManager: Error clearing last overfill time: {e}')
            
    # In-memory storage for GM fault count
    _gm_fault_count = 0
    
    def get_gm_fault_count(self) -> int:
        """
        Get the current GM fault count.
        
        Returns:
            The current fault count from memory
        """
        return self._gm_fault_count
    
    def increment_gm_fault_count(self) -> None:
        """Increment the GM fault count by 1."""
        try:
            self._gm_fault_count += 1
        except Exception as e:
            Logger.error(f'AlarmManager: Error incrementing GM fault count: {e}')
    
    def reset_gm_fault_count(self) -> None:
        """Reset the GM fault count to 0."""
        try:
            self._gm_fault_count = 0
        except Exception as e:
            Logger.error(f'AlarmManager: Error resetting GM fault count: {e}')
    
    def get_vac_pump_failure_count(self) -> int:
        """
        Get the current vacuum pump failure count.
        
        Returns:
            The current failure count
        """
        try:
            # Get the count from alarms_db
            failure_count = self.app.alarms_db.get_setting('vac_pump_failure_count')
            if failure_count is not None:
                return int(failure_count)
                
            # If not found in alarms_db, return 0
            # This ensures the alarm is cleared when vac_pump_failure_count is None
            return 0
        except Exception as e:
            Logger.error(f'AlarmManager: Error getting vac pump failure count: {e}')
            return 0
    
    def increment_vac_pump_failure_count(self) -> None:
        """Increment the vacuum pump failure count by 1."""
        try:
            count = self.get_vac_pump_failure_count()
            # Store the incremented count in alarms_db
            self.app.alarms_db.add_setting('vac_pump_failure_count', count + 1)
            pass
        except Exception as e:
            Logger.error(f'AlarmManager: Error incrementing vac pump failure count: {e}')
    
    def reset_vac_pump_failure_count(self) -> None:
        """Reset the vacuum pump failure count to 0 and re-enable shutdown relay."""
        try:
            # Reset the count in alarms_db
            self.app.alarms_db.add_setting('vac_pump_failure_count', 0)
            
            # Clear vac pump alarm flag
            self.app.gm_db.add_setting('vac_pump_alarm', False)
            
            # Re-enable shutdown relay when vac pump alarm is cleared
            if hasattr(self.app, 'io') and hasattr(self.app.io, 'set_shutdown_relay'):
                self.app.io.set_shutdown_relay(True, 'vac_pump')
                Logger.info('AlarmManager: Vac pump alarm cleared, shutdown relay re-enabled')
            
            pass
        except Exception as e:
            Logger.error(f'AlarmManager: Error resetting vac pump failure count: {e}')
    
    def get_variable_pressure_point(self) -> Optional[float]:
        """
        Get the reference pressure point for variable pressure check.
        
        Returns:
            The reference pressure point, or None if not set
        """
        try:
            value = self.app.alarms_db.get_setting('variable_pressure_point')
            return float(value) if value is not None else None
        except Exception as e:
            Logger.error(f'AlarmManager: Error getting variable pressure point: {e}')
            return None
    
    def set_variable_pressure_point(self, pressure: float) -> None:
        """
        Set the reference pressure point for variable pressure check.
        
        Args:
            pressure: The pressure value to save
        """
        try:
            self.app.alarms_db.add_setting('variable_pressure_point', pressure)
        except Exception as e:
            Logger.error(f'AlarmManager: Error setting variable pressure point: {e}')
    
    def log_notification(self, message: str) -> None:
        """
        Log a notification to the system notifications database.
        
        Args:
            message: The notification message
        """
        # Notifications removed - using Logger instead
        pass


class Alarm:
    """
    Base class for system alarms with state tracking and persistence.
    
    This class handles the core alarm functionality including:
    - State tracking (active/inactive)
    - Duration requirements tracking
    - Database persistence
    - Notification generation
    """
    
    def __init__(
        self, 
        name: str, 
        condition: AlarmCondition, 
        duration: float,
        repository: Optional[AlarmRepository] = None
    ):
        """
        Initialize an alarm.
        
        Args:
            name: Unique name for the alarm
            condition: The condition object that determines when this alarm triggers
            duration: The duration (in seconds) the condition must exist before alarm triggers
            repository: The repository for alarm persistence (optional, will create a new one if not provided)
        """
        self.app = MDApp.get_running_app()
        self.name = name.lower().replace(' ', '_')
        self.duration = duration
        self.condition = condition
        
        # Create repository if not provided
        self.repository = repository if repository is not None else AlarmRepository()
            
        # Initialize remaining properties
        self.start_time = self.repository.get_start_time(self.name)
        
        # If alarm has a start time from database, it was previously triggered
        # Restore the triggered state to maintain alarm persistence across reboots
        if self.start_time is not None:
            # Check if enough time has passed for this alarm to be considered triggered
            current_time = datetime.now()
            elapsed_time = (current_time - self.start_time).total_seconds()
            
            if elapsed_time >= self.duration:
                self.time_triggered = self.start_time + timedelta(seconds=self.duration)
                Logger.info(f'AlarmManager: Restored active alarm state for {self.name} (started {self.start_time})')
            else:
                self.time_triggered = None
                Logger.debug(f'AlarmManager: Restored pending alarm state for {self.name} (started {self.start_time}, needs {self.duration - elapsed_time:.1f}s more)')
        else:
            self.time_triggered = None
            
        self.previous_pressure = None
    
    
    def get_elapsed_time(self, current_time: datetime) -> float:
        """
        Get the elapsed time since the alarm condition was first detected.
        
        Args:
            current_time: The current datetime
        
        Returns:
            The elapsed time in seconds
        """
        if not self.start_time:
            return 0
        return (current_time - self.start_time).total_seconds()
    
    def update_start_time(self, time_difference: timedelta) -> None:
        """
        Update the alarm start time based on a time difference.
        
        Args:
            time_difference: The time difference to apply
        """
        if self.start_time:
            self.start_time += time_difference
            self.repository.save_start_time(self.name, self.start_time)
    
    def update(self) -> bool:
        '''
        Update the alarm state based on the current condition
        '''
        current_time = datetime.now()
        self.start_time = self.repository.get_start_time(self.name)
        
        # Check if the alarm condition is met
        condition_met = self.condition.check(self)
        
        if condition_met:
            # If condition is met but start time not set, record the start time
            if self.start_time is None:
                self.start_time = current_time
                self.repository.save_start_time(self.name, self.start_time)
 
            # Check if the condition has existed long enough to trigger the alarm
            elapsed_time = self.get_elapsed_time(current_time)

            if elapsed_time >= self.duration:
                # Only execute actions when transitioning from inactive to active

                if not self.time_triggered:
                    self.time_triggered = current_time
                    self.repository.log_notification(f'{self.name} alarm triggered.')
                    
                    # Execute pressure sensor specific actions here after duration confirmation
                    if self.name == 'pressure_sensor':
                        self.app.io.stop_cycle()
                        if not self.app.pressure_sensor_alarm:
                            self.app.toggle_pressure_sensor_alarm(True)

                        # Turn OFF shutdown relay for pressure sensor alarm (CS9 profile only)
                        if hasattr(self.app, 'io') and hasattr(self.app.io, 'set_shutdown_relay'):
                            self.app.io.set_shutdown_relay(False, 'pressure_sensor')

                return True

        else:
            # Condition is no longer met - handle clearing
            # Only clear alarms that were actually triggered (time_triggered is not None)
            should_clear = (self.time_triggered is not None)
            
            if should_clear:
                self.repository.log_notification(f'{self.name} alarm cleared.')
                
                # Execute clearing actions based on alarm type
                if self.name == 'pressure_sensor':
                    # Clearing actions for pressure sensor - only when actually triggered
                    if hasattr(self.app, 'io') and hasattr(self.app.io, 'set_shutdown_relay'):
                        self.app.io.set_shutdown_relay(True, 'pressure_sensor')
                        Logger.info(f'AlarmManager: {self.name} alarm cleared, shutdown relay re-enabled')
                    
                    # Clear the pressure sensor alarm flag in the app
                    if hasattr(self.app, 'pressure_sensor_alarm'):
                        if self.app.pressure_sensor_alarm:
                            self.app.toggle_pressure_sensor_alarm(False)

                elif self.name == 'vac_pump':
                    # Re-enable shutdown relay when vac pump alarm is cleared
                    if hasattr(self.app, 'io') and hasattr(self.app.io, 'set_shutdown_relay'):
                        self.app.io.set_shutdown_relay(True, 'vac_pump')
                        Logger.info(f'AlarmManager: {self.name} alarm cleared, shutdown relay re-enabled')
                
                # Mark shutdown-triggering alarms as cleared for 72-hour tracking
                # Note: This list includes all possible shutdown-triggering alarms across all profiles
                shutdown_triggering_alarms = [
                    'low_pressure', 'high_pressure', 'under_pressure',
                    'over_pressure', 'pressure_sensor', 'zero_pressure',
                    'variable_pressure', 'digital_storage', 'vac_pump'
                ]
                
                if self.name in shutdown_triggering_alarms:
                    if hasattr(self.app, 'alarm_manager'):
                        self.app.alarm_manager.mark_shutdown_alarm_cleared(self.name)
            
            # Always clear database state when condition is no longer met
            self.repository.clear_start_time(self.name)
            self.start_time = None
            self.time_triggered = None
        
        return False


# Alarm Condition Implementations


class PressureSensorCondition(AlarmCondition):
    '''Condition for pressure sensor failure.'''
    
    def check(self, context: Alarm) -> bool:
        '''
        Returns True if pressure is below current low pressure threshold, False otherwise
        '''
        low_pressure_current_threshold = context.repository.get_threshold(
            'low_pressure_current', -40.0
        )
        pressure = self._get_pressure(context)
        
        # Only return condition status - no immediate actions
        # Actions will be taken after 5-second confirmation in Alarm.update()
        return float(pressure) < float(low_pressure_current_threshold)


class GMFaultCondition(AlarmCondition):
    """Condition for GM fault checking."""
    
    def check(self, context: Alarm) -> bool:
        """
        Check if GM fault count has exceeded threshold.
        
        Returns:
            True if GM fault count exceeds threshold, False otherwise
        """
        try:
            # Only check GM faults for CS9 profile
            profile = context.app.user_db.get_setting('profile')
            if profile != 'CS9':
                return False
                
            # Get threshold from database, use 3 as default if not set
            threshold = int(context.repository.get_threshold('gm_fault_count', 3))
            fault_count = int(context.repository.get_gm_fault_count())
            
            # If fault_count is 0, the alarm should be cleared
            if fault_count == 0:
                return False
                
            if fault_count >= threshold:
                context.app.io.stop_cycle()
                pass
                
                # Trigger vac pump alarm by setting failure count
                context.repository.increment_vac_pump_failure_count()
                context.app.gm_db.add_setting('vac_pump_alarm', True)
                
                pass
                
                return True
            return False
        except Exception as e:
            Logger.error(f'AlarmManager: Error in GM fault check: {e}')
            return False


class VacPumpCondition(AlarmCondition):
    """Condition for vacuum pump failure."""
    
    def check(self, context: Alarm) -> bool:
        """
        Check if vacuum pump has failed too many times or if GM faults exceed threshold (CS9 only).
        
        Returns:
            True if vac pump failure count exceeds threshold or GM faults exceed threshold (CS9), False otherwise
        """
        try:
            # Get profile to check if we need to consider GM faults
            profile = context.app.user_db.get_setting('profile')
            
            # Check vac pump failures
            vac_threshold = int(context.repository.get_threshold('vac_pump_fault_count', 10))
            failure_count = int(context.repository.get_vac_pump_failure_count())
            
            # Check if vac pump failures exceed threshold
            if failure_count >= vac_threshold:
                context.app.io.stop_cycle()
                pass
                return True
            
            # Check GM faults if in CS9 profile
            if profile == 'CS9':
                # Check GM faults
                gm_threshold = int(context.repository.get_threshold('gm_fault_count', 3))
                gm_fault_count = int(context.repository.get_gm_fault_count())
                
                # Check if GM faults exceed threshold
                if gm_fault_count >= gm_threshold:
                    context.app.io.stop_cycle()
                    pass
                    return True
            
            return False
        except Exception as e:
            Logger.error(f'AlarmManager: Error in vac pump check: {e}')
            return False


class VariablePressureCondition(AlarmCondition):
    """Condition for variable pressure alarm."""
    
    def check(self, context: Alarm) -> bool:
        """
        Check if pressure has not changed beyond threshold within time period.
        
        Returns:
            True if pressure hasn't changed enough, False otherwise
        """
        threshold = float(context.repository.get_threshold('variable_pressure', 0.20))
        current_pressure = float(self._get_pressure(context))
        pressure_point = context.repository.get_variable_pressure_point()
        
        if pressure_point is None:
            pressure_point = current_pressure
            context.repository.set_variable_pressure_point(pressure_point)
            return False
            
        # Check if the change in pressure exceeds the threshold from starting point
        if abs(float(pressure_point) - current_pressure) <= abs(threshold):
            return True
        else:
            context.repository.set_variable_pressure_point(current_pressure)
            return False


class ZeroPressureCondition(AlarmCondition):
    """Condition for zero pressure alarm."""
    
    def check(self, context: Alarm) -> bool:
        """
        Check if pressure is near zero.
        
        Returns:
            True if pressure is within zero threshold range, False otherwise
        """
        threshold = float(context.repository.get_threshold('zero_pressure', 0.15))
        current_pressure = float(self._get_pressure(context))
        
        # Check if the current pressure is within the threshold range of 0.00 ± threshold
        return abs(current_pressure) <= abs(threshold)


class OverPressureCondition(AlarmCondition):
    """Condition for high pressure alarm."""
    
    def check(self, context: Alarm) -> bool:
        """
        Check if pressure exceeds high threshold.
        
        Returns:
            True if pressure is above threshold, False otherwise
        """
        try:
            # Get threshold value with error handling
            try:
                threshold = context.repository.get_threshold('over_pressure', 2.0)
            except Exception as e:
                Logger.error(f'AlarmManager: Error getting over_pressure threshold: {e}')
                return False
            
            # Get pressure with error handling
            try:
                pressure = self._get_pressure(context)
            except Exception as e:
                Logger.error(f'AlarmManager: Error getting pressure for over_pressure check: {e}')
                return False
            
            # Compare pressure to threshold
            return float(pressure) >= float(threshold)
        except Exception as e:
            Logger.error(f'AlarmManager: Error in over_pressure check: {e}')
            return False


class UnderPressureCondition(AlarmCondition):
    """Condition for low pressure alarm."""
    
    def check(self, context: Alarm) -> bool:
        """
        Check if pressure is below low threshold.
        
        Returns:
            True if pressure is below threshold, False otherwise
        """
        try:
            # Get threshold value with error handling
            try:
                threshold = context.repository.get_threshold('under_pressure', -6.0)
            except Exception as e:
                Logger.error(f'AlarmManager: Error getting under_pressure threshold: {e}')
                return False
            
            # Get pressure with error handling
            try:
                pressure = self._get_pressure(context)
            except Exception as e:
                Logger.error(f'AlarmManager: Error getting pressure for under_pressure check: {e}')
                return False
            
            # Compare pressure to threshold
            return float(pressure) <= float(threshold)
        except Exception as e:
            Logger.error(f'AlarmManager: Error in under_pressure check: {e}')
            return False


class OverfillCondition(AlarmCondition):
    """Condition for overfill alarm."""
    
    def check(self, context: Alarm) -> bool:
        """
        Check if overfill condition exists.
        
        Returns:
            True if overfill is detected, False otherwise
        """
        current_time = datetime.now()
        last_overfill_time = context.repository.get_last_overfill_time()
        
        # ==================================================================
        # SERIAL-ONLY: Overfill detection from ESP32 serial data.
        # ESP32 reads GPIO38 (TLS input) with 8/5 hysteresis validation
        # (8 consecutive HIGH readings to trigger, 5 consecutive LOW to
        # clear) and sends the overfill status in every 15-second status
        # JSON packet. This is the ONLY overfill detection source —
        # the I2C MCP23017 TLS pin read has been removed.
        #
        # The ESP32's hysteresis validation is MORE robust than a single
        # pin read because it filters out transient noise spikes.
        # ==================================================================
        try:
            serial_mgr = getattr(context.app, 'serial_manager', None)
            if serial_mgr and serial_mgr.esp32_overfill:
                context.app.io.stop_cycle()
                context.repository.save_last_overfill_time(current_time)
                return True
        except Exception as e:
            Logger.error(f'AlarmManager: Error reading serial overfill: {e}')
        
        # Maintain alarm state if overfill was detected within last 2 hours
        if last_overfill_time and (current_time - last_overfill_time) < timedelta(hours=2):
            return True
        
        return False


class DigitalStorageCondition(AlarmCondition):
    """Condition for digital storage (SD card) alarm."""
    
    def check(self, context: Alarm) -> bool:
        """
        Check if digital storage condition exists.
        
        Returns:
            True if digital storage is not available, False otherwise
        """
        # Try the safe method first, fallback to original if needed
        try:
            return self._check_mounts_safe()
        except Exception:
            # Fallback to original method if safe method fails
            return self._check_mounts_original()
    
    def _check_mounts_safe(self) -> bool:
        """Safe mount checking without signal conflicts - USB crash fix."""
        import subprocess
        import time
        
        try:
            # Add small delay to avoid checking during active USB mounting/unmounting
            time.sleep(0.05)
            
            # Use subprocess with longer timeout but NO signal handlers to avoid USB event conflicts
            result = subprocess.run(
                ['lsblk', '-o', 'MOUNTPOINT,TYPE'],
                capture_output=True,
                text=True,
                timeout=8  # Increased timeout to handle USB mounting delays
            )
            
            if result.returncode == 0 and '/media' in result.stdout:
                return False
            else:
                self._clear_mount_directory_safe()
                return True
                
        except subprocess.TimeoutExpired:
            # If lsblk times out, it might be due to USB activity - assume storage unavailable
            Logger.warning('AlarmManager: lsblk command timed out during USB activity, assuming storage unavailable')
            self._clear_mount_directory_safe()
            return True
        except subprocess.CalledProcessError as e:
            # If lsblk fails, assume storage unavailable
            Logger.warning(f'AlarmManager: lsblk command failed: {e}, assuming storage unavailable')
            self._clear_mount_directory_safe()
            return True
        except Exception as e:
            # Any other error, assume storage unavailable
            Logger.warning(f'AlarmManager: Unexpected error in mount check: {e}, assuming storage unavailable')
            self._clear_mount_directory_safe()
            return True
    
    def _check_mounts_original(self) -> bool:
        """Original mount checking method as fallback."""
        try:
            # Original code with shorter timeout
            import os
            mounts = os.popen('lsblk -o MOUNTPOINT,TYPE').read()
            if '/media' in mounts:
                return False
            else:
                self._clear_mount_directory()
                return True
        except Exception:
            # If everything fails, assume storage unavailable
            return True
    
    def _clear_mount_directory_safe(self) -> None:
        """Clear leftover mount points without signal conflicts - USB crash fix."""
        try:
            # Simple cleanup without signal handlers to avoid USB event conflicts
            self._clear_mount_directory()
        except OSError as e:
            # If cleanup fails due to USB activity or permissions, just log and continue
            Logger.warning(f'AlarmManager: Mount directory cleanup failed (likely due to USB activity): {e}')
        except Exception as e:
            # Any other error during cleanup - not critical, just log
            Logger.warning(f'AlarmManager: Unexpected error during mount directory cleanup: {e}')
    
    def _clear_mount_directory(self) -> None:
        """Original clear mount directory method."""
        directory = '/media/cpx003'
        try:
            # Check if directory exists
            if os.path.exists(directory):
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                pass


class SeventyTwoHourCondition(AlarmCondition):
    """
    Condition for 72-hour shutdown alarm.
    
    This class now uses the cached result from the separate 72-hour checker
    instead of doing expensive calculations every time.
    """
    
    def check(self, context: Alarm) -> bool:
        """
        Check if conditions exist that would eventually lead to a 72-hour shutdown.
        
        This now simply returns the cached state from the separate 72-hour checker,
        eliminating the expensive nested loop calculations that were causing UI lag.
        
        Returns:
            True if alarm conditions that lead to 72-hour shutdown exist and have been
            active for at least 72 hours, False otherwise
        """
        try:
            # Use cached result from the separate 72-hour checker
            # This eliminates all the expensive nested loop logic
            if hasattr(context.app, 'alarm_manager') and hasattr(context.app.alarm_manager, '_cached_72_hour_state'):
                return context.app.alarm_manager._cached_72_hour_state
            
            # Fallback to False if cache not available (shouldn't happen in normal operation)
            Logger.warning('AlarmManager: 72-hour cache not available, returning False')
            return False
            
        except Exception as e:
            Logger.error(f'AlarmManager: Error in SeventyTwoHourCondition check: {e}')
            return False


class AlarmManager:
    """
    Manages system alarms and coordinates alarm-related activities.
    
    This class is responsible for:
    - Creating and initializing all system alarms
    - Periodically checking alarm conditions
    - Tracking active alarms
    - Coordinating alarm responses
    """
    
    def __init__(self):
        """Initialize the alarm manager."""
        self.app = None  # Will be set when get_running_app() is available
        self.repository = AlarmRepository()
        self.alarms = []
        self.active_alarms: Set[str] = set()
        self._stop_event = threading.Event()
        self._alarm_thread = None
        
        # Separate 72-hour checker attributes
        self._72_hour_check_event = None
        self._shutdown_alarm_changes = set()
        self._cached_72_hour_state = False
        self._last_72_hour_check = 0
        
    def initialize_alarms(self) -> None:
        '''
        Initialize alarms based on current profile.
        
        This method is now profile-aware and only creates alarms that are
        appropriate for the current profile. The ProfileHandler is responsible
        for determining which alarms should be active.
        
        Note: This method is now primarily called as a fallback. The preferred
        method is to use ProfileHandler.load_alarms() which creates profile-specific
        alarms directly.
        '''
        # Ensure app reference is available
        if not self.app:
            self.app = MDApp.get_running_app()
        
        # Clear existing alarms
        self.alarms = []
        
        # Let ProfileHandler create the appropriate alarms for current profile
        if hasattr(self.app, 'profile_handler'):
            try:
                self.app.profile_handler.load_alarms()
                Logger.info(f'AlarmManager: Profile-specific alarms initialized via ProfileHandler')
                return
            except Exception as e:
                Logger.error(f'AlarmManager: Error loading profile alarms: {e}')
        
        # Fallback: Create basic alarms if ProfileHandler is not available
        Logger.warning('AlarmManager: ProfileHandler not available, creating basic alarm set')
        basic_alarms = [
            Alarm(
                name="pressure_sensor",
                condition=PressureSensorCondition(),
                duration=10.0,
                repository=self.repository
            ),
            Alarm(
                name="vac_pump",
                condition=VacPumpCondition(),
                duration=0.0,
                repository=self.repository
            ),
            Alarm(
                name="overfill",
                condition=OverfillCondition(),
                duration=0.0,
                repository=self.repository
            ),
            Alarm(
                name="digital_storage",
                condition=DigitalStorageCondition(),
                duration=0.0,
                repository=self.repository
            )
        ]
        self.alarms = basic_alarms
        
    def start_alarm_thread(self) -> None:
        """Start a thread for checking alarms."""
        # Don't start a new thread if one is already running
        if self._alarm_thread and self._alarm_thread.is_alive():
            return
            
        self._stop_event.clear()
        self._alarm_thread = threading.Thread(
            target=self._run_alarm_checks,
            daemon=True,
            name="AlarmCheckerThread"
        )
        self._alarm_thread.start()
        Logger.info(f'AlarmManager: Alarm checker thread started')
        
        # Start separate 72-hour checker
        self.start_72_hour_checker()
    
    def stop_alarm_thread(self) -> None:
        """Stop the alarm checking thread."""
        self._stop_event.set()
        if self._alarm_thread and self._alarm_thread.is_alive():
            self._alarm_thread.join(timeout=2.0)
            Logger.info(f'AlarmManager: Alarm checker thread stopped')
        
        # Stop separate 72-hour checker
        self.stop_72_hour_checker()
    
    def start_72_hour_checker(self) -> None:
        """Start separate 72-hour checking process using Kivy Clock."""
        try:
            from kivy.clock import Clock
            if self._72_hour_check_event is None:
                self._72_hour_check_event = Clock.schedule_interval(
                    self.check_72_hour_conditions,
                    300  # Every 5 minutes - non-blocking
                )
                Logger.info('AlarmManager: 72-hour checker started (5-minute intervals)')
        except Exception as e:
            Logger.error(f'AlarmManager: Error starting 72-hour checker: {e}')
    
    def stop_72_hour_checker(self) -> None:
        """Stop the separate 72-hour checker."""
        try:
            if self._72_hour_check_event is not None:
                self._72_hour_check_event.cancel()
                self._72_hour_check_event = None
                Logger.info('AlarmManager: 72-hour checker stopped')
        except Exception as e:
            Logger.error(f'AlarmManager: Error stopping 72-hour checker: {e}')
    
    def mark_shutdown_alarm_cleared(self, alarm_name: str) -> None:
        """Mark that a shutdown-triggering alarm was cleared."""
        self._shutdown_alarm_changes.add(alarm_name)
        Logger.debug(f'AlarmManager: Marked {alarm_name} for 72-hour check')
    
    def check_72_hour_conditions(self, dt=None) -> None:
        """
        Separate 72-hour condition checker - runs every 5 minutes.
        This contains the expensive logic moved from Alarm.update().
        """
        try:
            import time
            current_time = datetime.now()
            shutdown_duration = 72 * 60 * 60  # 72 hours in seconds
            
            # Ensure app reference is available
            if not self.app:
                self.app = MDApp.get_running_app()
            
            # Get profile to determine which alarms to check
            try:
                profile = self.app.user_db.get_setting('profile')
                if profile is None:
                    profile = 'CS8'
            except Exception:
                profile = 'CS8'
            
            # Define shutdown-triggering alarm names based on profile
            if profile == 'CS8':
                shutdown_triggering_alarms = [
                    'low_pressure', 'high_pressure', 'under_pressure',
                    'over_pressure', 'pressure_sensor', 'zero_pressure',
                    'variable_pressure', 'digital_storage', 'vac_pump'
                ]
            elif profile == 'CS9':
                shutdown_triggering_alarms = ['vac_pump', 'pressure_sensor']
            elif profile == 'CS12':
                shutdown_triggering_alarms = ['pressure_sensor']
            else:
                shutdown_triggering_alarms = []
            
            # Check if any shutdown-triggering alarms have been active for 72+ hours
            shutdown_condition_met = False
            active_72_hour_alarms = []
            
            for alarm in self.alarms:
                if (alarm.name in shutdown_triggering_alarms and
                    alarm.start_time and
                    (current_time - alarm.start_time).total_seconds() >= shutdown_duration):
                    shutdown_condition_met = True
                    active_72_hour_alarms.append(alarm.name)
            
            # Log if condition changed
            if shutdown_condition_met != self._cached_72_hour_state:
                if shutdown_condition_met:
                    Logger.info(f'AlarmManager: 72-hour shutdown condition met for alarms: {active_72_hour_alarms}')
                else:
                    Logger.info('AlarmManager: 72-hour shutdown condition cleared')
            
            # Update 72-hour shutdown alarm state
            self._update_72_hour_shutdown_state(shutdown_condition_met)
            
            # Cache the result and update timestamp
            self._cached_72_hour_state = shutdown_condition_met
            self._last_72_hour_check = time.time()
            
            # Clear the change tracking
            self._shutdown_alarm_changes.clear()
            
        except Exception as e:
            Logger.error(f'AlarmManager: Error in 72-hour check: {e}')
    
    def _update_72_hour_shutdown_state(self, condition_met: bool) -> None:
        """Update the 72-hour shutdown alarm state."""
        try:
            # Find the 72-hour shutdown alarm
            for alarm in self.alarms:
                if alarm.name == '72_hour_shutdown':
                    if condition_met:
                        # Activate 72-hour shutdown
                        if not alarm.start_time:
                            alarm.start_time = datetime.now()
                            alarm.repository.save_start_time(alarm.name, alarm.start_time)
                            alarm.time_triggered = alarm.start_time
                            if hasattr(self.app, 'toggle_shutdown'):
                                self.app.toggle_shutdown(True)
                            Logger.info('AlarmManager: 72-hour shutdown activated')
                    else:
                        # Clear 72-hour shutdown
                        if alarm.start_time:
                            alarm.repository.clear_start_time(alarm.name)
                            alarm.start_time = None
                            alarm.time_triggered = None
                            if hasattr(self.app, 'toggle_shutdown'):
                                self.app.toggle_shutdown(False)
                            Logger.info('AlarmManager: 72-hour shutdown cleared')
                    break
        except Exception as e:
            Logger.error(f'AlarmManager: Error updating 72-hour shutdown state: {e}')
    
    def _run_alarm_checks(self) -> None:
        """Run periodic alarm checks."""
        # Set up exception handling for the thread
        try:
            while not self._stop_event.is_set():
                self.check_alarms()
                # Sleep for 1 second between checks
                time.sleep(1)
        except Exception as e:
            Logger.error(f'AlarmManager: Error in alarm checker thread: {e}')
            # Try to restart the thread
            time.sleep(5)
            if not self._stop_event.is_set():
                self._alarm_thread = threading.Thread(
                    target=self._run_alarm_checks, 
                    daemon=True,
                    name="AlarmCheckerThread"
                )
                self._alarm_thread.start()
    
    def check_alarms(self) -> None:
        """Check all alarms and update active alarm list."""
        # Ensure app reference is available
        if not self.app:
            self.app = MDApp.get_running_app()
            
        # Ensure alarms are initialized - but don't force initialization
        # Let ProfileHandler manage alarm creation based on current profile
        if not self.alarms:
            # Only initialize if ProfileHandler hasn't created alarms yet
            if hasattr(self.app, 'profile_handler'):
                try:
                    self.app.profile_handler.load_alarms()
                except Exception as e:
                    Logger.error(f'AlarmManager: Error loading profile alarms in check_alarms: {e}')
                    # Fallback to basic initialization
                    self.initialize_alarms()
            else:
                # No ProfileHandler available, use basic initialization
                self.initialize_alarms()
            
        # Check each alarm and update active alarm set
        currently_active = set()
        try:
            for alarm in self.alarms:
                try:
                    if alarm.update():
                        currently_active.add(alarm.name)
                except Exception as e:
                    Logger.error(f'AlarmManager: Error checking alarm {alarm.name}: {e}')
            
            # Special check for 72_hour_shutdown alarm
            # It should be cleared if no shutdown-triggering alarms have been active for 72 hours
            if '72_hour_shutdown' in currently_active:
                # Get the profile to determine which alarms to check
                profile = self.app.user_db.get_setting('profile')
                if profile is None:
                    profile = 'CS8'
                
                # Define shutdown-triggering alarm names based on profile
                if profile == 'CS8':
                    shutdown_triggering_alarms = [
                        'low_pressure', 'high_pressure', 'under_pressure',
                        'over_pressure', 'pressure_sensor', 'zero_pressure',
                        'variable_pressure', 'digital_storage', 'vac_pump'
                    ]
                elif profile == 'CS9':
                    shutdown_triggering_alarms = ['vac_pump', 'pressure_sensor']
                elif profile == 'CS12':
                    shutdown_triggering_alarms = ['pressure_sensor']
                else:
                    shutdown_triggering_alarms = []
                
                # Check if any shutdown-triggering alarms are active for 72 hours
                current_time = datetime.now()
                shutdown_duration = 72 * 60 * 60  # 72 hours in seconds
                shutdown_condition_met = False
                
                for alarm in self.alarms:
                    if (alarm.name in shutdown_triggering_alarms and
                        alarm.name in currently_active and
                        alarm.start_time and
                        (current_time - alarm.start_time).total_seconds() >= shutdown_duration):
                        shutdown_condition_met = True
                        break
                
                # If no shutdown-triggering alarms have been active for 72 hours, clear the 72_hour_shutdown alarm
                if not shutdown_condition_met:
                    Logger.info(f'AlarmManager: Clearing 72_hour_shutdown alarm as no triggering alarms have been active for 72 hours')
                    currently_active.discard('72_hour_shutdown')
                    
                    # Find the 72_hour_shutdown alarm and clear its start time
                    for alarm in self.alarms:
                        if alarm.name == '72_hour_shutdown':
                            alarm.repository.clear_start_time(alarm.name)
                            alarm.start_time = None
                            alarm.time_triggered = None
                            break
                    
                    # Make sure shutdown state is cleared
                    if hasattr(self.app, 'shutdown') and self.app.shutdown:
                        self.app.toggle_shutdown(False)
            
            # Update active alarms set
            self.active_alarms = currently_active
        except Exception as e:
            Logger.error(f'AlarmManager: Error in check_alarms: {e}')
    
    def get_active_alarms(self) -> List[str]:
        """
        Get the list of active alarm names.
        
        Returns:
            List of active alarm names
        """
        return list(self.active_alarms)
    
    def update_alarm_start_times(self, time_difference: timedelta) -> None:
        """
        Update the start times of all alarms based on a time difference.
        
        Args:
            time_difference: The time difference to apply
        """
        for alarm in self.alarms:
            alarm.update_start_time(time_difference)
    
    def add_alarm(self, alarm: Alarm) -> None:
        """
        Add an alarm to the managed alarms list.
        
        Args:
            alarm: The alarm instance to add
        """
        self.alarms.append(alarm)
        Logger.debug(f'AlarmManager: Added alarm: {alarm.name}')
    
    def get_alarm_names(self) -> List[str]:
        """
        Get the names of all currently managed alarms.
        
        Returns:
            List of alarm names
        """
        return [alarm.name for alarm in self.alarms]
    
    def has_alarm(self, alarm_name: str) -> bool:
        """
        Check if a specific alarm is currently managed.
        
        Args:
            alarm_name: The name of the alarm to check
            
        Returns:
            True if the alarm exists, False otherwise
        """
        return any(alarm.name == alarm_name for alarm in self.alarms)
    
    def clear_alarms(self) -> None:
        """Reset all alarms and clear any active states."""
        # Clear active_alarms set
        self.active_alarms.clear()
        
        # Clear any alarm start times from database for existing alarms
        for alarm in self.alarms:
            try:
                alarm.repository.clear_start_time(alarm.name)
            except Exception as e:
                Logger.error(f'AlarmManager: Error clearing start time for {alarm.name}: {e}')
        
        # If the app has a shutdown state, reset it
        if hasattr(self, 'app') and self.app and hasattr(self.app, 'shutdown') and self.app.shutdown:
            self.app.toggle_shutdown(False)
            
        # Reset alarm instances
        self.alarms = []
        
        # Clear cached 72-hour state
        self._cached_72_hour_state = False
        self._last_72_hour_check = 0
        self._shutdown_alarm_changes.clear()
        
        Logger.info('AlarmManager: All alarms cleared and states reset')
    
    def reset_alarm_instances_only(self) -> None:
        """
        Reset only alarm instances without clearing persistent database states.
        
        This method is used during profile changes and startup to reinitialize
        alarm objects while preserving any existing alarm states in the database.
        This ensures alarm persistence across system reboots.
        """
        # Clear active_alarms set (will be rebuilt from database)
        self.active_alarms.clear()
        
        # Reset alarm instances only - DO NOT clear database states
        self.alarms = []
        
        # Clear cached 72-hour state (will be recalculated)
        self._cached_72_hour_state = False
        self._last_72_hour_check = 0
        self._shutdown_alarm_changes.clear()
        
        Logger.info('AlarmManager: Alarm instances reset (database states preserved)')
