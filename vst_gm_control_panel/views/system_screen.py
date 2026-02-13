'''
System Management Screen
'''

# Standard imports.
from datetime import datetime

# Kivy imports.
from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty, ObjectProperty, StringProperty

# Local imports.
from components import CustomDialog


class SystemScreen(MDScreen):
    '''
    SystemScreen:
    - This class sets up the System Management Screen.
    '''

    input_string = StringProperty('')
    new_interval = NumericProperty()
    current_interval_name = StringProperty()
    current_interval_value = NumericProperty()
    current_sheet = ObjectProperty()
    shutdown_time = StringProperty('4320')  # 72 hours in minutes
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.intervals = {
            'shutdown_time': 4320  # 72 hours
        }

    def return_to_main(self):
        '''Return to the main screen'''
        self.app.root.current = 'main'

    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        '''
        pass

    def open_keypad(self, keypad_sheet, caller):
        '''
        Open the keypad sheet for interval entry.
        '''
        self.current_interval_name = caller
        
        # Store the current value for comparison in the dialog
        if caller in self.intervals:
            self.current_interval_value = self.intervals[caller]
        
        keypad_sheet.drawer_type = 'modal'
        keypad_sheet.set_state('toggle')
        self.current_sheet = keypad_sheet
        
        # Initialize the input string with the current value
        if caller == 'shutdown_time':
            self.input_string = self.shutdown_time
        else:
            self.input_string = ''
            
        # Update the input field display
        self.update_input_field()

    def update_input_field(self):
        '''
        Update the input field to show the current input string followed by the unit.
        '''
        if self.current_interval_name == 'shutdown_time':
            self.ids.input_field.text = f"{self.input_string} min"
        else:
            self.ids.input_field.text = self.input_string

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
        Submit the interval entry.
        '''
        code_entered = self.input_string
        try:
            value = int(code_entered)
            # Store the value directly without conversion - we'll handle conversion in confirm_value_change
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

        if self.current_interval_name == 'shutdown_time':
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
        if self.current_interval_name == 'shutdown_time':
            # Get the value in minutes
            minutes = int(self.input_string)
            
            # Call the app's method to set the test shutdown time
            self.app.set_test_shutdown_time(minutes)
            
            # Update our local property for UI display
            self.shutdown_time = str(minutes)
            
            pass
            
            # Mark as user-defined if not default
            if minutes != 4320:  # 4320 minutes = 72 hours (default)
                self.app.user_defined_change()
        
        self.new_interval = 0
        self.current_sheet.set_state('toggle')