'''
Timezone Selection Screen
'''

# Standard imports
from datetime import datetime
import subprocess
import time
import pytz
from zoneinfo import ZoneInfo

# Kivy imports
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER
from components import CustomDialog

class TimezoneSelectionScreen(BaseOOBEScreen):
    '''
    Timezone Selection Screen:
    - This screen allows the user to verify the current system timezone.
    - It provides options to navigate through timezones and select one.
    '''
    
    current_time = StringProperty('')
    current_timezone = StringProperty('')
    display_timezone = StringProperty('')
    available_timezones = ListProperty([])
    timezone_index = 0
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "TIMEZONE VERIFICATION"
        self.load_available_timezones()
        self.get_current_timezone()
        Clock.schedule_interval(self.update_time, 1)
        
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        '''
        self.get_current_timezone()
        
    def get_current_timezone(self):
        '''
        Get the current system timezone and update the display.
        '''
        # Get current timezone from system or app settings
        try:
            # Try to get from system
            with open('/etc/timezone', 'r') as f:
                self.current_timezone = f.read().strip()
        except:
            # Fallback to app settings
            self.current_timezone = self.app.oobe_db.get_setting('timezone', 'UTC')
            
        self.display_timezone = self.current_timezone
        self.timezone_index = self.get_timezone_index(self.display_timezone)
        self.update_time()
            
    def load_available_timezones(self):
        '''
        Load a list of common timezones.
        '''
        # Only America and Mexico timezones
        self.available_timezones = [
            'UTC',
            # US timezones
            'America/New_York',       # Eastern Time
            'America/Chicago',        # Central Time
            'America/Denver',         # Mountain Time
            'America/Los_Angeles',    # Pacific Time
            'America/Anchorage',      # Alaska Time
            'America/Adak',           # Hawaii-Aleutian Time
            'Pacific/Honolulu',       # Hawaii Time
            
            # Mexico timezones
            'America/Mexico_City',    # Mexico City (Central Time)
            'America/Cancun',         # Cancun (Eastern Time)
            'America/Chihuahua',      # Chihuahua (Mountain Time)
            'America/Hermosillo',     # Hermosillo (Mountain Time - no DST)
            'America/Tijuana',        # Tijuana (Pacific Time)
            'America/Mazatlan',       # Mazatlan (Mountain Time)
            'America/Monterrey',      # Monterrey (Central Time)
            
            # Canada timezones
            'America/Toronto',        # Eastern Time
            'America/Winnipeg',       # Central Time
            'America/Edmonton',       # Mountain Time
            'America/Vancouver',      # Pacific Time
            'America/St_Johns'        # Newfoundland Time
        ]
        
    def update_time(self, *args):
        '''
        Update the current time display with the selected timezone.
        '''
        try:
            tz = pytz.timezone(self.display_timezone)
            now = datetime.now(tz)
            self.current_time = now.strftime('%H:%M')
        except:
            # Fallback to UTC if timezone is invalid
            now = datetime.now(pytz.UTC)
            self.current_time = now.strftime('%H:%M')
    
    def get_timezone_index(self, timezone):
        '''
        Get the index of a timezone in the available_timezones list.
        '''
        try:
            return self.available_timezones.index(timezone)
        except ValueError:
            return 0  # Default to UTC if not found
    
    def next_timezone(self):
        '''
        Navigate to the next timezone in the list.
        '''
        self.timezone_index = (self.timezone_index + 1) % len(self.available_timezones)
        self.display_timezone = self.available_timezones[self.timezone_index]
        self.update_time()
        
    def previous_timezone(self):
        '''
        Navigate to the previous timezone in the list.
        '''
        self.timezone_index = (self.timezone_index - 1) % len(self.available_timezones)
        self.display_timezone = self.available_timezones[self.timezone_index]
        self.update_time()
        
    def on_verify(self):
        '''
        Handle verification of the current timezone.
        '''
        # If timezone was changed, update the system timezone
        if self.display_timezone != self.current_timezone:
            self.set_system_timezone(self.display_timezone)
            
        # Mark timezone verification as complete in the OOBE database
        self.app.oobe_db.add_setting('timezone_verified', 'true')
        self.app.oobe_db.add_setting('timezone', self.display_timezone)
        
        # Get the selected profile from the database
        selected_profile = self.app.oobe_db.get_setting('profile', '')
        
        # If the profile is CS2, skip the CRE number entry screen
        if selected_profile == 'CS2':
            # Mark CRE number entry as not required for CS2 profile
            self.app.oobe_db.add_setting('cre_number_entered', 'true')
            
            # Navigate to the Contractor Certification screen
            self.next_screen('OOBEContractorCertification')
        else:
            # Navigate to the CRE number entry screen
            self.next_screen('OOBECRENumber')
            
    def _check_all_oobe_complete(self):
        '''
        Check if all OOBE steps are complete.
        
        Returns:
            bool: True if all steps are complete, False otherwise
        '''
        # Check all OOBE flags
        language_selected = self.app.oobe_db.get_setting('language_selected', 'false') == 'true'
        profile_selected = self.app.oobe_db.get_setting('profile_selected', 'false') == 'true'
        power_info_acknowledged = self.app.oobe_db.get_setting('power_info_acknowledged', 'false') == 'true'
        date_verified = self.app.oobe_db.get_setting('date_verified', 'false') == 'true'
        timezone_verified = self.app.oobe_db.get_setting('timezone_verified', 'false') == 'true'
        gm_serial_entered = self.app.oobe_db.get_setting('gm_serial_entered', 'false') == 'true'
        cre_number_entered = self.app.oobe_db.get_setting('cre_number_entered', 'false') == 'true'
        contractor_certification_entered = self.app.oobe_db.get_setting('contractor_certification_entered', 'false') == 'true'
        
        # Return True if all flags are true
        return (language_selected and profile_selected and
                power_info_acknowledged and date_verified and
                timezone_verified and gm_serial_entered and
                cre_number_entered and contractor_certification_entered)
                
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
            
    def set_system_timezone(self, timezone):
        '''
        Set the system timezone.
        '''
        try:
            # Set the timezone using timedatectl
            subprocess.run(['sudo', 'timedatectl', 'set-timezone', timezone], check=True)
            Logger.info(f'OOBE: System timezone set to {timezone}')
            
            # Update the current timezone
            self.current_timezone = timezone
            
            # Update Python's runtime timezone setting
            import os
            os.environ['TZ'] = timezone
            time.tzset()  # Apply the timezone change to the current process
            
            # Force refresh of time display
            self.update_time()
            
            # Update any time-dependent systems if needed
            if hasattr(self.app, 'get_datetime'):
                self.app.get_datetime()
                
            # Schedule another update after a short delay to ensure all widgets are updated
            Clock.schedule_once(lambda dt: self.update_time(), 0.5)
                
        except subprocess.CalledProcessError as e:
            Logger.error(f'OOBE: Error setting system timezone: {e}')
            # Continue with the flow even if timezone setting fails
            
    def go_back(self):
        '''
        Navigate to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)