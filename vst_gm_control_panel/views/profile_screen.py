'''
Profile Selection Screen
'''

# Standard imports
from datetime import datetime

# Kivy imports
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty

# Local imports
from components import CustomDialog


class ProfileScreen(MDScreen):
    '''
    ProfileScreen:
    - This class sets up the Profile Selection Screen.
    - Allows switching between different system profiles (CS8, CS2, CS9, CS12, TEST)
    '''

    current_profile = StringProperty('')
    name = StringProperty('profile')  # This matches the name used in admin_screen.open_profile_screen()

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.update_current_profile()

    def on_enter(self):
        '''Called when the screen is entered'''
        self.update_current_profile()

    def update_current_profile(self):
        '''Update the current profile display'''
        self.current_profile = self.app.profile_handler.profile

    def switch_profile(self, profile):
        '''
        Switch to a different profile.
        
        Args:
            profile (str): The profile to switch to
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('confirm_profile_switch', 'Confirm Profile Switch?')
        text_start = self.app.language_handler.translate(
            'confirm_profile_switch_message',
            'Are you sure you want to switch to profile {}?'.format(profile)
        )
        text_end = self.app.language_handler.translate(
            'dialog_confirmation',
            "Click 'Accept' to confirm or 'Cancel' to return."
        )

        text = f'{text_start}\n\n{text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=lambda: self.confirm_profile_switch(profile),
            cancel=cancel
        )

    def confirm_profile_switch(self, profile):
        '''
        Confirm and execute the profile switch.
        
        Args:
            profile (str): The profile to switch to
        '''
        # Save the new profile
        self.app.profile_handler.save_profile(profile)
        
        # Update both profile handler and main app profile
        self.app.profile_handler.profile = profile
        self.app.profile = profile  # This will trigger property change events
        
        # Reload alarms for the new profile
        self.app.profile_handler.load_alarms()
        
        # Update the display
        self.current_profile = profile
        
        pass
        
        # Check if we were in admin mode before switching
        was_admin_mode = self.app.admin_mode
        was_admin_level = self.app.user_access_level == 4
        
        # Return to maintenance screen to refresh button states
        self.app.switch_screen('Maintenance')
        
        # Restore admin mode if it was active before profile switch
        if was_admin_mode and was_admin_level:
            self.app.admin_mode = True
            self.app.user_access_level = 4
            # Refresh the access timeout since we're preserving admin access
            self.app.refresh_access_timeout()