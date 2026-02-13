'''
Profile Selection Screen
'''

# Kivy imports
from kivymd.uix.button import MDButton, MDButtonText

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER


class ProfileSelectionScreen(BaseOOBEScreen):
    '''
    Profile Selection Screen:
    - This screen allows the user to select their system profile.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "PROFILE SELECTION"
        
    def on_profile_selected(self, profile):
        '''
        Handle profile selection.
        
        Args:
            profile (str): The selected profile (CS2, CS8, CS9, or CS12)
        '''
        # Update profile in the app
        self.app.profile = profile
        self.app.profile_handler.save_profile(profile)
        
        # Also save the profile to the oobe_db for the OOBE flow
        self.app.oobe_db.add_setting('profile', profile)
        
        # Mark profile selection as complete
        self.app.oobe_db.add_setting('profile_selected', 'true')

        self.next_screen('OOBEPanelSerial')
        
    def go_back(self):
        '''
        Navigate to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)