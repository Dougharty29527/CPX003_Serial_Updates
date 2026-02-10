'''
System Config Screen
'''
# Standard imports.
import time
from datetime import datetime, timedelta

# Kivy imports.
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty, ObjectProperty, StringProperty

# Local imports.
from components import ConfirmationDialog, CustomDialog


class SystemConfigScreen(MDScreen):
    '''
    This class sets up the System Config Screen.
    '''

    input_string = StringProperty('')
    current_threshold = StringProperty()
    low_limit = StringProperty('-0.55')
    high_limit = StringProperty('-0.35')
    run_time = StringProperty('15')
    rest_time = StringProperty('5')
    current_sheet = ObjectProperty()
    test_mode_time_elapsed = NumericProperty(0)
    start_time = NumericProperty(0)
    MAX_LENGTH = 5

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        
    def on_enter(self):
        '''Ensure any running cycles are stopped for safety.'''
        self.app.stop_any_cycle()
        # Set start time if test mode is active
        if self.app.test_mode:
            self.start_time = self.app.test_mode_start

    def open_keypad(self, keypad_sheet, caller):
        '''Open the keypad sheet.'''
        self.caller = caller
        keypad_sheet.drawer_type = 'modal'
        keypad_sheet.set_state('toggle')
        self.current_sheet = keypad_sheet
        if caller == 'low_limit':
            self.input_string = self.low_limit
        elif caller == 'high_limit':
            self.input_string = self.high_limit
        elif caller == 'run_time':
            self.input_string = self.run_time
        elif caller == 'rest_time':
            self.input_string = self.rest_time
        self.ids.input_field.text = self.input_string
        self.update_input_field()

    def add_digit(self, digit):
        '''Add a digit to the input field.'''
        self.input_string += str(digit)
        self.update_input_field()

    def backspace(self):
        '''Remove the last digit from the input field.'''
        self.input_string = self.input_string[:-1]
        self.update_input_field()

    def submit(self):
        '''Submit the value for the system configuration.'''
        code_entered = self.input_string
        self.value_change_dialog(code_entered)

    def change_value(self, code_entered):
        '''Change the value of the system configuration.'''
        if self.caller == 'low_limit':
            self.low_limit = code_entered
        if self.caller == 'high_limit':
            self.high_limit = code_entered
        if self.caller == 'run_time':
            self.run_time = code_entered
        if self.caller == 'rest_time':
            self.rest_time = code_entered
        self.app.update_test_mode_values(self.low_limit, self.high_limit, self.run_time, self.rest_time)

    def update_input_field(self):
        '''Update the input field to show the current input string followed by the unit.'''
        input_string = ''
        if self.caller == 'low_limit' or self.caller == 'high_limit':
            self.ids.input_field.text = f"{self.input_string} UST"
        elif self.caller == 'run_time' or self.caller == 'rest_time':
            self.ids.input_field.text = f"{self.input_string} sec"

    def confirm_test_dialog(self):
        '''Confirmation popup with detailed information about test mode.'''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('enable_system_config', 'Enable System Config Mode?')
        text_start = self.app.language_handler.translate('confirm_system_config_message', 'Are you sure you want to enable system config mode?')
        text_end = self.app.language_handler.translate('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return.")
        
        text = f'{text_start}\n\n{text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.start_test,
            cancel=cancel
        )

    def start_test(self):
        '''Start the test mode - now delegated to main application.'''
        # Check conditions but don't start if blocked
        conditions = self.app.check_cycle_conditions('test_mode')
        if conditions:
            self.show_alarm_dialog()
            return
        # Initialize test mode through the main application
        self.app.start_test_mode(
            self.low_limit, self.high_limit, self.run_time, self.rest_time
        )

    def stop_test(self):
        '''Stop the test mode - now delegated to main application.'''
        # Reset local state
        self.start_time = 0    
        self.app.stop_test_mode()

    def show_alarm_dialog(self):
        '''Show the dialog box.'''
        dialog = ConfirmationDialog()
        title = self.app.language_handler.translate('alarm_dialog_title', 'Alarms Detected')
        text_start = self.app.language_handler.translate(
            'alarm_dialog_one', 'Cannot start the test while alarms are active.'
        )
        text_end = self.app.language_handler.translate(
            'alarm_dialog_two', 'Please acknowledge or resolve all alarms before proceeding.'
        )
        text = f'{text_start}\n\n{text_end}'
        accept = 'OK'

        if self.app.language == 'ES':
            accept = self.app.language_handler.translate('accept', 'Aceptar')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept
        )

    def value_change_dialog(self, code_entered):
        '''Confirmation popup.'''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('confirm_value_override', 'Confirm Value Override?')
        text_start = self.app.language_handler.translate('confirm_interval_change_message', 'Are you sure you want to modify the system default interval?')
        text_end = self.app.language_handler.translate('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return.")

        current_value = ''
        new_value = ''

        if self.caller == 'low_limit':
            current_value = '-0.55 UST'
            new_value = f'{code_entered} UST'
        elif self.caller == 'high_limit':
            current_value = '-0.35 UST'
            new_value = f'{code_entered} UST'
        elif self.caller == 'run_time':
            current_value = '15 seconds'
            new_value = f'{code_entered} seconds'
        elif self.caller == 'rest_time':
            current_value = '5 seconds'
            new_value = f'{code_entered} seconds'

        text = f'{text_start}\n{current_value} > {new_value}\n\n{text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=lambda: self.change_value(code_entered),
            cancel=cancel
        )
        self.ids.input_field.text = ''
