'''
Panel Serial Screen
'''

# Kivy imports
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER


class PanelSerialScreen(BaseOOBEScreen):
    '''
    Panel Serial Screen:
    - This screen allows the user to enter the panel serial number.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "PANEL SERIAL NUMBER"
        self.serial_number = ""
        
    def add_character(self, char):
        '''
        Add a character to the input field.
        '''
        current_text = self.ids.serial_input.text
        self.ids.serial_input.text = current_text + str(char)
        
    def delete_character(self):
        '''
        Remove a character from the input field.
        '''
        current_text = self.ids.serial_input.text
        
        if len(current_text) >= 1:
            current_text = current_text[:-1]
            self.ids.serial_input.text = current_text
        
    def on_serial_entered(self):
        '''
        Handle panel serial number entry.
        Accepts any number entered.
        '''
        # Get the serial number from the text field
        serial_field = self.ids.serial_input
        self.serial_number = serial_field.text.strip()
        
        if not self.serial_number:
            # Show error if serial number is empty
            serial_field.error = True
            serial_field.helper_text = "Panel serial number cannot be empty"
            return
            
        # Save the panel serial number to the database
        self.app.gm_db.add_setting('panel_serial', self.serial_number)
        
        # Mark panel serial entry as complete
        self.app.oobe_db.add_setting('panel_serial_entered', 'true')
        
        # Navigate to the GM serial screen
        self.next_screen('OOBEGMSerial')
        
    def go_back(self):
        '''
        Navigate to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)