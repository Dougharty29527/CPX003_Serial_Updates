'''
CRE Number Screen
'''

# Kivy imports
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER


class CRENumberScreen(BaseOOBEScreen):
    '''
    CRE Number Screen:
    - This screen allows the user to enter the station CRE number.
    - This screen is only displayed if the profile selected is NOT CS2.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "CRE NUMBER"
        self.cre_number = ""
        
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        Check if the profile is CS2, if so, skip this screen.
        '''
        # Get the selected profile from the database
        selected_profile = self.app.oobe_db.get_setting('profile', '')
        
        # If the profile is CS2, skip this screen
        if selected_profile == 'CS2':
            # Mark CRE number entry as not required for CS2 profile
            self.app.oobe_db.add_setting('cre_number_entered', 'true')
            
            # Navigate to the next screen
            self._go_to_next_screen()
        
    def add_character(self, char):
        '''
        Add a character to the input field.
        '''
        current_text = self.ids.cre_input.text
        self.ids.cre_input.text = current_text + str(char)
        
    def delete_character(self):
        '''
        Remove a character from the input field.
        '''
        current_text = self.ids.cre_input.text
        
        if len(current_text) >= 1:
            current_text = current_text[:-1]
            self.ids.cre_input.text = current_text
        
    def on_cre_entered(self):
        '''
        Handle CRE number entry.
        '''
        # Get the CRE number from the text field
        cre_field = self.ids.cre_input
        self.cre_number = cre_field.text.strip()
        
        if not self.cre_number:
            # Show error if CRE number is empty
            cre_field.error = True
            cre_field.helper_text = "CRE number cannot be empty"
            return
            
        # Save the CRE number to both databases
        # OOBE database for flow control
        self.app.oobe_db.add_setting('cre_number', self.cre_number)
        # GM database for runtime access
        self.app.gm_db.add_setting('cre_number', self.cre_number)
        
        # Mark CRE number entry as complete
        self.app.oobe_db.add_setting('cre_number_entered', 'true')
        
        # Navigate to the Contractor Certification screen
        self.next_screen('OOBEContractorCertification')
        
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
        
    def go_back(self):
        '''
        Navigate to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)