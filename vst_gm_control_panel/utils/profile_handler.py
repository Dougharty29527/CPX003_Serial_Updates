"""
ProfileHandler:
- This module is used to manage user profiles and load profile-specific alarms.
"""

# Standard imports
from datetime import datetime

# Kivy imports
from kivymd.app import MDApp
from kivy.logger import Logger

# Local imports
from .alarm_manager import (
    Alarm, PressureSensorCondition, VacPumpCondition,
    OverPressureCondition, UnderPressureCondition,
    VariablePressureCondition, ZeroPressureCondition,
    OverfillCondition, DigitalStorageCondition,
    SeventyTwoHourCondition, AlarmCondition,
    GMFaultCondition
)


class ProfileHandler:
    """
    Class for handling profiles and profile-specific alarm configurations.
    """

    def __init__(self):
        """Initialize the profile handler."""
        self.app = MDApp.get_running_app()
        self.profile = self.load_profile()
        self.load_alarms()

    def load_profile(self):
        """
        Load the current profile from the database.
        
        Returns:
            str: The current profile name
        """
        profile = self.app.user_db.get_setting('profile')
        if profile is None:
            profile = 'CS8'
            self.save_profile(profile)
        return profile

    def save_profile(self, profile):
        """
        Save the current profile to the database and update related components.
        
        Args:
            profile (str): Profile name to save
        """
        try:
            # Save profile to database
            self.app.user_db.add_setting('profile', profile)
            
            # Update internal profile
            self.profile = profile
            
            pass
            
            # Reload alarms for new profile
            self.load_alarms()
            
            # Rebuild faults screen if it exists
            if hasattr(self.app, 'sm'):
                faults_screen = self.app.sm.get_screen('Faults')
                if faults_screen:
                    faults_screen.update_alarm_screen()
                    
            return True
            
        except Exception as e:
            return False

    def get_alarms(self):
        """
        Get a list of alarms based on the current profile.
        
        Returns:
            list: List of alarm names for the current profile
        """
        alarms_dict = {
            'CS8': [
                'Pressure Sensor',
                'Vac Pump',
                'Overfill',
                'Digital Storage',
                'Under Pressure',
                'Over Pressure',
                'Zero Pressure',
                'Variable Pressure',
                '72 Hour Shutdown'
            ],
            'CS2': [
                'Pressure Sensor',
                'Vac Pump',
                'Overfill',
                'Digital Storage'
            ],
            'CS9': [
                'Pressure Sensor',
                'Vac Pump',
                'Overfill',
                'Digital Storage',
                'GM Fault',
                '72 Hour Shutdown'
            ],
            'CS12': [
                'Pressure Sensor',
                'Vac Pump',
                'Overfill',
                'Digital Storage',
                '72 Hour Shutdown'
            ],
            'TEST': [
                '72 Hour Shutdown'
            ]
        }
        return alarms_dict.get(self.profile, [])

    def load_alarms(self):
        """
        Load the alarms for the current profile.
        
        Creates alarm conditions based on profile configuration and
        adds them to the alarm manager.
        
        Returns:
            bool: True if alarms were loaded successfully, False otherwise
        """
        try:
            # Reset alarm instances only (preserve database states for safety)
            self.app.alarm_manager.reset_alarm_instances_only()
            
            # Get shutdown time setting
            seventy_two_hour_time = (
                self.app.modified_shutdown_time
                if self.app.test_shutdown_time
                else 259200
            )
            
            pass
            
            # Initialize default delays
            default_delays = {
                'pressure_sensor': 10,
                'vac_pump': 0,
                'over_pressure': 1800,  # 30 minutes
                'under_pressure': 1800,  # 30 minutes
                'variable_pressure': 3600,  # 60 minutes
                'zero_pressure': 3600,  # 60 minutes
                'overfill': 0,
                'digital_storage': 0,
                '72_hour_shutdown': seventy_two_hour_time,
                'gm_fault': 0  # GM Fault is immediate
            }

            # Get profile-specific alarm settings based on current profile
            if self.profile == 'CS2':
                # CS2 only uses basic alarms with default settings
                alarm_delays = {
                    key: default_delays[key]
                    for key in ['pressure_sensor', 'vac_pump', 'overfill', 'digital_storage']
                }
            elif self.profile == 'CS9':
                # CS9 uses basic alarms plus GM Fault and 72 Hour Shutdown
                alarm_delays = {
                    key: default_delays[key]
                    for key in ['pressure_sensor', 'vac_pump', 'overfill', 'digital_storage', 'gm_fault', '72_hour_shutdown']
                }
            elif self.profile == 'CS12':
                # CS12 uses basic alarms plus 72 Hour Shutdown
                alarm_delays = {
                    key: default_delays[key]
                    for key in ['pressure_sensor', 'vac_pump', 'overfill', 'digital_storage', '72_hour_shutdown']
                }
            elif self.profile == 'TEST':
                # TEST only uses 72 Hour Shutdown
                alarm_delays = {
                    key: default_delays[key]
                    for key in ['72_hour_shutdown']
                }
            else:
                # CS8 and others use all alarms with configurable delays
                alarm_delays = default_delays.copy()

            pass

            # Map alarm names to their condition classes
            condition_map = {
                'Pressure Sensor': PressureSensorCondition(),
                'Vac Pump': VacPumpCondition(),
                'Over Pressure': OverPressureCondition(),
                'Under Pressure': UnderPressureCondition(),
                'Variable Pressure': VariablePressureCondition(),
                'Zero Pressure': ZeroPressureCondition(),
                'Overfill': OverfillCondition(),
                'Digital Storage': DigitalStorageCondition(),
                '72 Hour Shutdown': SeventyTwoHourCondition(),
                'GM Fault': GMFaultCondition()
            }

            # Create alarm conditions based on profile's allowed alarms
            alarm_conditions = {}
            alarms_list = self.get_alarms()
            
            for alarm_name in alarms_list:
                # Convert alarm name to settings key format
                settings_key = alarm_name.lower().replace(' ', '_')
                
                # Get the delay from profile-specific settings
                delay = alarm_delays.get(settings_key, 0)
                
                # If in debug mode, use shorter delays
                if self.app.debug:
                    # Keep immediate alarms at 0
                    if delay > 0:
                        # Use 30s for short delays, 60s for long delays
                        delay = 30 if delay <= 1800 else 60
                
                # Create the alarm condition tuple
                if alarm_name in condition_map:
                    alarm_conditions[alarm_name] = (condition_map[alarm_name], delay)

            # Create and add alarms for this profile
            created_alarms = []
            for alarm_name in alarms_list:
                condition, duration = alarm_conditions.get(alarm_name, (None, None))
                if condition and duration is not None:
                    # Create alarm with the condition strategy
                    alarm = Alarm(
                        name=alarm_name,
                        condition=condition,
                        duration=duration
                    )
                    # Add to alarm manager
                    self.app.alarm_manager.add_alarm(alarm)
                    created_alarms.append(alarm_name)
                else:
                    pass  # Log missing condition/duration if needed
            
            # Log successful alarm creation for debugging
            Logger.info(f'ProfileHandler: Created {len(created_alarms)} alarms for profile {self.profile}: {created_alarms}')
                    
            return True
            
        except Exception as e:
            return False
