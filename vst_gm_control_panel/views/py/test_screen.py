from kivymd.uix.screen import MDScreen
from kivy.properties import BooleanProperty, StringProperty

''' 
Test Screen.

This module defines the MainScreen class, which represents the main screen of the application.
'''


class TestScreen(MDScreen):
    '''
    Test Screen
    -----------
    This class sets up the Testing Screen.
    '''

    pin_entry = BooleanProperty(False)
    interval_entry = BooleanProperty(False)
    input_string = StringProperty('0')

    def __init__(self, app, **kwargs):
        '''
        Parameters:
            app (App): The main application instance.
            name (str, optional): The name of the screen. Defaults to None.
        '''
        super().__init__(**kwargs)
        self.app = app

    def open_sheet(self, sheet, drawer_type):
        if self.pin_entry:
            self.interval_entry = False
        else:
            self.pin_entry = False
        self.input_string = '0'
        sheet.drawer_type = drawer_type
        sheet.set_state('toggle')

    def add_digit(self, digit):
        ''' Add a digit to the Test screen. '''
        current_text = self.app.sm.get_screen('Test').ids.input_field.text
        if self.app.sm.get_screen('Test').ids.input_field.text == '0':
            self.app.sm.get_screen('Test').ids.input_field.text = str(digit)
        else:
            self.app.sm.get_screen('Test').ids.input_field.text = current_text + str(digit)

    def backspace(self):
        ''' Remove a digit from the Test screen. '''
        current_text = self.app.sm.get_screen('Test').ids.input_field.text
        if len(current_text) == 1:
            self.app.sm.get_screen('Test').ids.input_field.text = '0'
        else:
            self.app.sm.get_screen('Test').ids.input_field.text = current_text[:-1]

    def submit(self):
        ''' Submit the code entered on the Test screen. '''
        code_entered = self.app.sm.get_screen('Test').ids.input_field.text
        if self.pin_entry:
            self.app.set_pin_delay(int(code_entered))
            self.input_string = f'{self.app.translate("pin_update", "Pin delay set to")} {code_entered} ms.'
        elif self.interval_entry:
            self.app.set_run_cycle_interval(int(code_entered))
            self.input_string = f'{self.app.translate("cycle_check_interval", "Run cycle check interval set to")} {code_entered} min.'
        self.pin_entry = False
        self.interval_entry = False
