'''
Test Intervals Screen
'''

# Standard imports.
from datetime import datetime
import os
import subprocess

# Kivy imports.
from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty, ObjectProperty, StringProperty

# Local imports.
from components import CustomDialog, Diagnostics

class AdminScreen(MDScreen):
    '''
    Test Screen:
    - This class sets up the Testing Screen.
    '''

    input_string = StringProperty('')
    new_interval = NumericProperty()
    current_interval_name = StringProperty()
    current_interval_value = NumericProperty()
    current_sheet = ObjectProperty()

    # Constants for default intervals
    DEFAULT_PIN_DELAY_MS = 10  # milliseconds

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.intervals = {
            'pin_delay': self.DEFAULT_PIN_DELAY_MS / 1000,
            'shutdown_time': 4320  # 72 hours
        }
        
    def open_profile_screen(self):
        '''
        Navigate to the profile selection screen.
        '''
        self.app.root.current = 'profile'

    def open_about_screen(self):
        '''
        Navigate to the about screen.
        '''
        self.app.root.current = 'About'

    def open_keypad(self, keypad_sheet, caller):
        '''
        Open the keypad sheet for pin and interval entry.
        '''
        if caller in self.intervals:
            self.current_interval_name = caller
            self.current_interval_value = self.intervals[caller]
        keypad_sheet.drawer_type = 'modal'
        keypad_sheet.set_state('toggle')
        self.current_sheet = keypad_sheet
        self.input_string = ''
        self.update_input_field()

    def update_input_field(self):
        '''
        Update the input field to show the current input string followed by the unit.
        '''
        if self.current_interval_name == 'pin_delay':
            self.ids.input_field.text = f"{self.input_string} ms"
        elif self.current_interval_name == 'shutdown_time':
            self.ids.input_field.text = f"{self.input_string} min"
        else:
            self.ids.input_field.text = self.input_string  # For shutdown or other cases without a unit.

    def add_digit(self, digit):
        '''
        Add a digit to the input field.
        '''
        self.input_string += str(digit)
        self.update_input_field()

    def backspace(self):
        '''
        Remove the last digit from the input field.
        '''
        self.input_string = self.input_string[:-1]
        self.update_input_field()

    def submit(self):
        '''
        Submit the pin or interval entry.
        '''
        code_entered = self.input_string
        try:
            value = int(code_entered)
            if self.current_interval_name == 'pin_delay':
                value /= 1000  # Convert milliseconds to seconds
            elif self.current_interval_name == 'shutdown_time':
                pass
            self.new_interval = value
            self.show_dialog()
        except ValueError:
            pass

    def show_dialog(self):
        '''
        Confirmation popup.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('confirm_value_override', 'Confirm Value Override?')
        text_start = self.app.language_handler.translate('confirm_interval_change_message', 'Are you sure you want to modify the system default interval?')
        text_end = self.app.language_handler.translate('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return.")

        current_value = ''
        new_value = ''

        if self.current_interval_name == 'pin_delay':
            current_value = f'{int(self.current_interval_value * 1000)} ms'
            new_value = f'{int(self.new_interval * 1000)} ms'
        elif self.current_interval_name == 'shutdown_time':
            current_value = f'4320 min (72 hours)'
            new_value = f'{self.new_interval} min'
        text = f'{text_start}\n{current_value} > {new_value}\n\n{text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.confirm_value_change,
            cancel=cancel
        )
        self.ids.input_field.text = ''

    def confirm_value_change(self):
        '''
        Confirm the value change and update the threshold.
        '''
        if self.current_interval_name == 'pin_delay':
            self.app.io.set_pin_delay(self.new_interval)
            self.app.pin_delay_string = f'{int(self.new_interval * 1000)} ms'
            if self.app.pin_delay_string != '10 ms':
                self.app.user_defined_change()
        elif self.current_interval_name == 'shutdown_time':
            self.app.set_test_shutdown_time(self.new_interval)
            if self.new_interval != 4320:
                self.app.user_defined_change()
        
        self.new_interval = 0
        self.current_sheet.set_state('toggle')

    def factory_reset(self):
        '''
        Factory reset the application.
        '''
        self.app.stop_any_cycle()
        # Use absolute path to ensure correct file is deleted
        vst_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        db_file = os.path.join(vst_root, 'data', 'db', 'app.db')
        try:
            os.remove(db_file)
        except FileNotFoundError:
            pass
        self.restart_application()

    def restart_application(self):
        '''
        Restart the application service.
        '''
        self.app.stop_any_cycle()
        try:
            os.system('sudo systemctl restart gm_control_panel.service')
        except OSError as e:
            pass

    def factory_reset_dialog(self):
        '''
        Factory reset confirmation dialog.
        '''

        title = self.app.language_handler.translate('confirm_factory_reset', 'Confirm Factory Reset?')
        text_start = self.app.language_handler.translate(
            'confirm_factory_reset_message', 'Are you sure you want to reset the application to factory settings?'
        )
        text_end = self.app.language_handler.translate(
            'factory_reset_details',
            'This action will restore all settings to their default values and erase all stored and any modified data. This cannot be undone.'
        )
        accept_method = self.factory_reset

        dialog = CustomDialog()
        dialog.open_dialog(
            title=title,
            text=f'{text_start}\n\n{text_end}',
            accept=self.app.language_handler.translate('accept', 'Accept'),
            accept_method=accept_method,
            cancel=self.app.language_handler.translate('cancel', 'Cancel')
        )
        