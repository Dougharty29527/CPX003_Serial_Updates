'''
Alarm Reload Utility
This module provides functionality to handle signal-triggered alarm state reloading,
allowing the application to recognize when alarms are cleared or modified by external scripts.
'''

import signal
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Kivy imports for thread-safe UI updates
from kivy.clock import Clock

# Local imports
from .database_manager import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)

# Debounce lock and timestamp
_reload_lock = threading.Lock()
_last_reload_time = 0
_min_reload_interval = 1.0  # seconds

def setup_signal_handlers(app):
    """
    Setup signal handlers for the application.
    
    Args:
        app: The main application instance
    """
    try:
        # Set up SIGUSR1 handler with debouncing
        signal.signal(signal.SIGUSR1, lambda sig, frame: debounced_reload_alarms(app))
        logger.info("Signal handlers initialized with debouncing")
    except Exception as e:
        logger.error(f"Error setting up signal handlers: {e}")

def debounced_reload_alarms(app):
    """
    Debounced wrapper for reload_alarms to prevent rapid signal processing.
    
    This function implements a debounce mechanism to ensure that rapid signals
    don't cause database issues by limiting the frequency of reloads.
    
    Args:
        app: The main application instance
    """
    global _last_reload_time
    
    # Get current time for debounce check
    current_time = time.time()
    
    # Use lock for thread safety
    with _reload_lock:
        # If reload was called too recently, ignore this call
        if current_time - _last_reload_time < _min_reload_interval:
            logger.info("Ignoring reload signal (within debounce period)")
            return
            
        # Update reload timestamp
        _last_reload_time = current_time
    
    # Queue the reload operation to avoid database contention
    logger.info("Queueing alarm reload operation")
    DatabaseManager.queue_operation(_do_reload_alarms, app)

def _do_reload_alarms(app):
    """
    Worker implementation of reload_alarms that runs in the database queue thread.
    
    This method performs database operations in the worker thread, but schedules
    any UI updates to occur on the main thread via Clock.schedule_once().
    
    Args:
        app: The main application instance
    """
    try:
        pass
        
        # Database operations only - no UI updates
        # ---------------------------------------
        # These operations are safe to run in a worker thread
        
        # Force AlarmManager to reinitialize alarms from database (preserve states)
        try:
            app.alarm_manager.reset_alarm_instances_only()
            app.profile_handler.load_alarms()
        except Exception as alarm_error:
            logger.error(f"Error reinitializing alarms: {alarm_error}")
        
        # Reload pressure calibration values from database
        _reload_calibration(app)
        
        # UI operations - must be scheduled on the main thread
        # --------------------------------------------------
        # Schedule alarm check on the main thread to prevent Kivy threading errors
        Clock.schedule_once(lambda dt: _main_thread_ui_updates(app), 0)
        
        pass
        logger.info("Alarm state reloaded due to external signal")
    except Exception as e:
        error_message = f"Error reloading alarm state: {e}"
        logger.error(error_message)
        pass

def _main_thread_ui_updates(app):
    """
    Perform UI updates on the main thread.
    
    This function is scheduled to run on the main thread, making it safe
    to perform UI operations like updating the alarm list and checking alarms.
    
    Args:
        app: The main application instance
    """
    try:
        # Reset UI-related alarm state
        app.alarm_list_last_check.clear()
        app.alarm_list.clear()
        
        # Force an immediate alarm check
        app.check_alarms()
        
        # Check if shutdown should be exited
        if hasattr(app, 'shutdown') and app.shutdown and not app.alarm:
            app.toggle_shutdown(False)
            logger.info("Exited shutdown mode after alarm state reload")
    except Exception as e:
        logger.error(f"Error performing UI updates after reload: {e}")

def _reload_calibration(app):
    """
    Reload and validate calibration values.
    
    This function reloads calibration values from the database and
    ensures they are within reasonable ranges to prevent calculation errors.
    
    Args:
        app: The main application instance
    """
    if not hasattr(app, 'io') or app.io is None:
        logger.warning("No IO manager available, skipping calibration reload")
        return
        
    try:
        # Get current calibration
        old_zero = app.io.pressure_sensor.adc_zero
        
        # Get new calibration
        new_zero = app.io.pressure_sensor.get_adc_zero()
        
        # Validate the calibration value is within a reasonable range
        # Default is around 15422.0, allow a reasonable range
        if new_zero is not None:
            if new_zero < 14000 or new_zero > 16500:
                logger.warning(
                    f"ADC zero calibration value {new_zero} is outside safe range (14000-16500). "
                    f"Using previous value {old_zero}."
                )
                # Use previous value instead of extreme value
                new_zero = old_zero
            
        # Update calibration
        app.io.pressure_sensor.adc_zero = new_zero
        
        pass
        
        # Clear any cached pressure readings
        app.io.pressure_sensor.pressure_readings.clear()
    except Exception as e:
        logger.error(f"Error updating calibration values: {e}")

def _add_notification(app, message: str) -> None:
    """
    Add a notification to the system with proper error handling.
    
    Args:
        app: The main application instance
        message: The notification message to add
    """
    # Notifications removed - using Logger instead
    pass
