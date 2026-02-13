'''
Base OOBE Screen
'''

# Kivy imports
from kivymd.uix.screen import MDScreen


# Centralized OOBE screen order - imported by all OOBE screens
OOBE_SCREEN_ORDER = [
    'LanguageSelection',
    'ProfileSelection',
    'PanelSerial',
    'GMSerial',
    'PowerInfo',
    'DateVerification',
    'TimezoneSelection',
    'CRENumber',
    'ContractorCertification',
    'ContractorPassword',
    'BreakerInfo',
    'QuickFunctionalityTest',
    'PressureCalibration',
    'OverfillOverride',
    'StartupCode'
]


class BaseOOBEScreen(MDScreen):
    '''
    Base OOBE Screen:
    - This class provides common functionality for all OOBE screens.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        
    def next_screen(self, screen_name):
        '''
        Navigate to the next screen in the OOBE flow.
        '''
        self.app.switch_screen(screen_name)
        
    def previous_screen(self, screen_name):
        '''
        Navigate to the previous screen in the OOBE flow.
        '''
        self.app.switch_screen(screen_name)
        
    def complete_oobe(self):
        '''
        Complete the OOBE process and go to the main screen.
        Only call this when all OOBE steps are truly complete.
        '''
        self.app.switch_screen('Main')
        
    def go_back_skipping_completed(self, screen_order):
        '''
        Navigate back in the OOBE flow, skipping completed screens and screens not applicable for the current profile.
        
        Args:
            screen_order (list): List of screen names in the OOBE flow order
        '''
        # Find the current screen's index in the flow
        current_screen_name = self.name.replace('OOBE', '')
        current_index = -1
        for i, screen in enumerate(screen_order):
            if screen == current_screen_name:
                current_index = i
                break
                
        if current_index < 0:
            # If the screen is not found in the flow, stay on the current screen
            return
            
        if current_index == 0:
            # If we're at the first screen, there's no previous screen to go back to
            # Just stay on the current screen
            return
        
        # Get the selected profile from the database
        selected_profile = self.app.oobe_db.get_setting('profile', '')
            
        # Start from the previous screen and go backwards
        i = current_index - 1
        while i >= 0:
            screen_name = screen_order[i]
            
            # Check if this screen should be skipped based on profile
            if screen_name == 'CRENumber' and selected_profile == 'CS2':
                # Skip CRE Number screen for CS2 profile
                i -= 1
                continue
                
            if screen_name == 'BreakerInfo' and selected_profile not in ['CS8', 'CS12']:
                # Skip Breaker Info screen for profiles other than CS8 and CS12
                i -= 1
                continue
                
            if screen_name == 'OverfillOverride' and selected_profile == 'CS2':
                # Skip Overfill Override screen for CS2 profile
                i -= 1
                continue
            
            # Check if this is one of the screens that should be skipped if completed
            if screen_name in ['QuickFunctionalityTest', 'PressureCalibration', 'OverfillOverride']:
                # Get the appropriate flag name
                if screen_name == 'QuickFunctionalityTest':
                    flag_name = 'quick_functionality_test_completed'
                elif screen_name == 'PressureCalibration':
                    flag_name = 'pressure_calibration_completed'
                elif screen_name == 'OverfillOverride':
                    flag_name = 'overfill_override_completed'
                
                # Check if this screen is completed
                is_completed = self.app.oobe_db.get_setting(flag_name, 'false') == 'true'
                
                # If completed, skip this screen and continue to the previous one
                if is_completed:
                    i -= 1
                    continue
            
            # Found a screen to go back to
            self.app.switch_screen(f'OOBE{screen_name}')
            return
            
        # If we've gone through all screens and they're all completed or not applicable,
        # just go to the first screen
        self.app.switch_screen(f'OOBE{screen_order[0]}')
        
    def go_to_next_incomplete_step(self, screen_order):
        '''
        Navigate to the next incomplete OOBE step.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        
        Args:
            screen_order (list): List of screen names in the OOBE flow order
        '''
        # Find the current screen's index in the flow
        current_screen_name = self.name.replace('OOBE', '')
        current_index = -1
        for i, screen in enumerate(screen_order):
            if screen == current_screen_name:
                current_index = i
                break
                
        if current_index < 0 or current_index >= len(screen_order) - 1:
            # If the screen is not found in the flow or we're at the last screen,
            # check if all steps are complete and go to the main screen if they are
            if self._check_all_oobe_complete():
                self.complete_oobe()
            return
            
        # Start from the next screen and go forwards
        i = current_index + 1
        while i < len(screen_order):
            screen_name = screen_order[i]
            
            # Get the appropriate flag name for this screen
            flag_name = self._get_flag_name_for_screen(screen_name)
            
            # Check if this screen is completed
            is_completed = self.app.oobe_db.get_setting(flag_name, 'false') == 'true'
            
            # Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride if completed
            if screen_name in ['QuickFunctionalityTest', 'PressureCalibration', 'OverfillOverride'] and is_completed:
                # Skip this screen and continue to the next one
                i += 1
                continue
            
            # Found a screen to go to
            self.app.switch_screen(f'OOBE{screen_name}')
            return
            
        # If we've gone through all remaining screens and they're all skippable,
        # check if ALL OOBE steps are complete before going to the main screen
        if self._check_all_oobe_complete():
            self.complete_oobe()
        else:
            # If not all steps are complete, go to the first screen
            # This ensures we don't skip incomplete steps
            self.app.switch_screen(f'OOBE{screen_order[0]}')
        
    def _get_flag_name_for_screen(self, screen_name):
        '''
        Get the flag name for a screen.
        
        Args:
            screen_name (str): The name of the screen
            
        Returns:
            str: The name of the flag for this screen
        '''
        # Map screen names to their corresponding flag names
        screen_to_flag = {
            'LanguageSelection': 'language_selected',
            'ProfileSelection': 'profile_selected',
            'GMSerial': 'gm_serial_entered',
            'PowerInfo': 'power_info_acknowledged',
            'DateVerification': 'date_verified',
            'TimezoneSelection': 'timezone_verified',
            'CRENumber': 'cre_number_entered',
            'ContractorCertification': 'contractor_certification_entered',
            'ContractorPassword': 'contractor_password_entered',
            'BreakerInfo': 'breaker_info_acknowledged',
            'QuickFunctionalityTest': 'quick_functionality_test_completed',
            'PressureCalibration': 'pressure_calibration_completed',
            'OverfillOverride': 'overfill_override_completed',
            'StartupCode': 'startup_code_entered'
        }
        
        return screen_to_flag.get(screen_name, '')
        
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
        contractor_password_entered = self.app.oobe_db.get_setting('contractor_password_entered', 'false') == 'true'
        breaker_info_acknowledged = self.app.oobe_db.get_setting('breaker_info_acknowledged', 'false') == 'true'
        quick_functionality_test_completed = self.app.oobe_db.get_setting('quick_functionality_test_completed', 'false') == 'true'
        pressure_calibration_completed = self.app.oobe_db.get_setting('pressure_calibration_completed', 'false') == 'true'
        overfill_override_completed = self.app.oobe_db.get_setting('overfill_override_completed', 'false') == 'true'
        startup_code_entered = self.app.oobe_db.get_setting('startup_code_entered', 'false') == 'true'
        
        # Return True if all flags are true
        return (language_selected and profile_selected and
                power_info_acknowledged and date_verified and
                timezone_verified and gm_serial_entered and
                cre_number_entered and contractor_certification_entered and
                contractor_password_entered and breaker_info_acknowledged and
                quick_functionality_test_completed and pressure_calibration_completed and
                overfill_override_completed and startup_code_entered)