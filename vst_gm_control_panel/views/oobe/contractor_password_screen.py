'''
Contractor Password Screen
'''

# Kivy imports
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER


class ContractorPasswordScreen(BaseOOBEScreen):
    '''
    Contractor Password Screen:
    - This screen allows the user to enter the Startup Contractor Password.
    - This screen comes after the Contractor Certification Number screen.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "CONTRACTOR PASSWORD"
        self.password = ""
        
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        '''
        self.password = ""
        # Clear the password input field
        self.ids.password_input.text = ""
        # Clear any error state
        self.ids.password_input.error = False
        self.ids.password_input.helper_text = ""
        
    def add_character(self, char):
        '''
        Add a character to the input field.
        '''
        current_text = self.ids.password_input.text
        self.ids.password_input.text = current_text + str(char)
        
    def delete_character(self):
        '''
        Remove a character from the input field.
        '''
        current_text = self.ids.password_input.text
        
        if len(current_text) >= 1:
            current_text = current_text[:-1]
            self.ids.password_input.text = current_text
        
    def on_password_entered(self):
        '''
        Handle Contractor Password entry.
        '''
        # Get the password from the text field
        password_field = self.ids.password_input
        self.password = password_field.text.strip()
        
        if not self.password:
            # Show error if password is empty
            password_field.error = True
            password_field.helper_text = "Password cannot be empty"
            return
            
        # Check if the password is correct (hardcoded to 1793)
        if self.password == "1793":
            # Mark password entry as complete
            self.app.oobe_db.add_setting('contractor_password_entered', 'true')
            
            # Get the selected profile from the database
            selected_profile = self.app.oobe_db.get_setting('profile', '')
            
            # Only show breaker info screen for CS8 and CS12 profiles
            if selected_profile in ['CS8', 'CS12']:
                # Navigate to the Breaker Info screen
                self.next_screen('OOBEBreakerInfo')
            else:
                # For other profiles, mark breaker info as not required
                self.app.oobe_db.add_setting('breaker_info_acknowledged', 'true')
                # Go to the next incomplete step (should be Quick Functionality Test)
                self._go_to_next_screen()
        else:
            # If password is incorrect, clear the input field and show error
            password_field.text = ""
            password_field.error = True
            password_field.helper_text = "Incorrect password"
        
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
            
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
        
        # Get the selected profile from the database
        selected_profile = self.app.oobe_db.get_setting('profile', '')
        
        # For profiles other than CS8 and CS12, breaker info is not required
        if selected_profile not in ['CS8', 'CS12']:
            breaker_info_acknowledged = True
        
        # Return True if all flags are true
        return (language_selected and profile_selected and
                power_info_acknowledged and date_verified and
                timezone_verified and gm_serial_entered and
                cre_number_entered and contractor_certification_entered and
                contractor_password_entered and breaker_info_acknowledged and
                quick_functionality_test_completed)
                
    def _go_to_next_incomplete_step(self):
        '''
        Navigate to the next incomplete OOBE step.
        '''
        # Check OOBE flags in order
        if self.app.oobe_db.get_setting('language_selected', 'false') != 'true':
            self.next_screen('OOBELanguageSelection')
        elif self.app.oobe_db.get_setting('profile_selected', 'false') != 'true':
            self.next_screen('OOBEProfileSelection')
        elif self.app.oobe_db.get_setting('gm_serial_entered', 'false') != 'true':
            self.next_screen('OOBEGMSerial')
        elif self.app.oobe_db.get_setting('power_info_acknowledged', 'false') != 'true':
            self.next_screen('OOBEPowerInfo')
        elif self.app.oobe_db.get_setting('date_verified', 'false') != 'true':
            self.next_screen('OOBEDateVerification')
        elif self.app.oobe_db.get_setting('timezone_verified', 'false') != 'true':
            self.next_screen('OOBETimezoneSelection')
        elif self.app.oobe_db.get_setting('cre_number_entered', 'false') != 'true':
            self.next_screen('OOBECRENumber')
        elif self.app.oobe_db.get_setting('contractor_certification_entered', 'false') != 'true':
            self.next_screen('OOBEContractorCertification')
        elif self.app.oobe_db.get_setting('breaker_info_acknowledged', 'false') != 'true':
            # Get the selected profile from the database
            selected_profile = self.app.oobe_db.get_setting('profile', '')
            
            # Only show breaker info screen for CS8 and CS12 profiles
            if selected_profile in ['CS8', 'CS12']:
                self.next_screen('OOBEBreakerInfo')
            else:
                # For other profiles, mark breaker info as not required
                self.app.oobe_db.add_setting('breaker_info_acknowledged', 'true')
                # Continue to the next step in the flow
                self._go_to_next_incomplete_step()
        elif self.app.oobe_db.get_setting('quick_functionality_test_completed', 'false') != 'true':
            self.next_screen('OOBEQuickFunctionalityTest')
        else:
            # If all steps are complete, go to the main screen
            self.complete_oobe()
    
    def go_back(self):
        '''
        Go back to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)