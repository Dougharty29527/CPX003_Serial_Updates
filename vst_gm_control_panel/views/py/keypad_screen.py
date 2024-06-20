from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

''' 
Test Screen.

This module defines the MainScreen class, which represents the main screen of the application.
'''



class KeypadScreen(MDScreen):
    '''
    Test Screen
    -----------
    This class sets up the Testing Screen.
    '''

    def __init__(self, app, **kwargs):
        '''
        Parameters:
            app (App): The main application instance.
            name (str, optional): The name of the screen. Defaults to None.
        '''
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the SideBar.
        '''
        self.app = MDApp.get_running_app()

    def add_digit(self, digit):
        ''' Add a digit to the keypad screen. '''
        current_text = self.app.sm.get_screen('Keypad').ids.input_field.text
        self.app.sm.get_screen('Keypad').ids.input_field.text = current_text + str(digit)

    def backspace(self):
        ''' Remove a digit from the keypad screen. '''
        current_text = self.app.sm.get_screen('Keypad').ids.input_field.text
        self.app.sm.get_screen('Keypad').ids.input_field.text = current_text[:-1]

    def submit(self):
        ''' Submit the code entered on the keypad screen. '''
        code_entered = self.app.sm.get_screen('Keypad').ids.input_field.text
        if self.app.pin_entry:
            self.app.pin_entry = False
            self.app.set_pin_delay(int(code_entered))
        elif self.app.interval_entry:
            self.app.interval_entry = False
            self.app.set_run_cycle_interval(int(code_entered))
        self.app.switch_screen('Main')

        self.app.sm.get_screen('Keypad').ids.input_field.text = ''
