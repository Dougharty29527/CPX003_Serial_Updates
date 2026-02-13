'''
Dispenser Shutdown Breaker Information Screen
'''

# Kivy imports
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER


class BreakerInfoScreen(BaseOOBEScreen):
    '''
    Breaker Information Screen:
    - This screen informs the user to ensure the dispenser shutdown breaker
      is currently in the open position.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "BREAKER INFORMATION"
    
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        Check if the profile is CS2 or CS9, if so, skip this screen with animation.
        '''
        # Get the selected profile from the database
        selected_profile = self.app.oobe_db.get_setting('profile', '')
        
        # If the profile is CS2 or CS9, skip this screen with animation
        if selected_profile in ['CS2', 'CS9']:
            # Mark breaker info as not required for CS2/CS9 profiles
            self.app.oobe_db.add_setting('breaker_info_acknowledged', 'true')
            
            # Add a small delay before transitioning
            Clock.schedule_once(lambda dt: self._go_to_next_screen(), 0.5)
        
    def on_continue(self):
        '''
        Handle continue button press.
        '''
        # Mark breaker info screen as acknowledged
        self.app.oobe_db.add_setting('breaker_info_acknowledged', 'true')
        
        # Navigate to the next screen
        self._go_to_next_screen()
        
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
    
    def go_back(self):
        '''
        Go back to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)