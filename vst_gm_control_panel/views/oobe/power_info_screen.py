'''
Power Information Screen
'''

# Kivy imports
from kivymd.uix.button import MDButton, MDButtonText

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER


class PowerInfoScreen(BaseOOBEScreen):
    '''
    Power Information Screen:
    - This screen informs the user that it is okay to power down the machine
      or if the machine shuts down or loses power throughout the setup,
      it will pick back up where they left off.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "POWER INFORMATION"
        
    def on_continue(self):
        '''
        Handle continue button press.
        '''
        # Mark power info screen as acknowledged
        self.app.oobe_db.add_setting('power_info_acknowledged', 'true')
        
        # Navigate to the next screen
        self.next_screen('OOBEDateVerification')
        
    def go_back(self):
        '''
        Navigate to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)