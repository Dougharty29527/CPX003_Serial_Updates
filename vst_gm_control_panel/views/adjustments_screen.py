'''
Adjustments Screen
'''

# Standard imports.
from datetime import datetime

# Kivy imports.
from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty, ObjectProperty, StringProperty

# Local imports.
from components import CustomDialog


class AdjustmentsScreen(MDScreen):
    '''
    AdjustmentsScreen:
    - This class sets up the Adjustments Screen.
    - Allows setting the shutdown interval and resetting to defaults.
    - Allows setting various alarm and pressure delay thresholds.
    '''

    input_string = StringProperty('')
    new_interval = NumericProperty()
    current_interval_name = StringProperty()
    current_interval_value = NumericProperty()
    current_sheet = ObjectProperty()
    shutdown_time = StringProperty('4320')  # 72 hours in minutes
    vac_pump_fault_count = StringProperty('10')
    high_pressure_delay = StringProperty('1800')  # 30 minutes in seconds
    low_pressure_delay = StringProperty('1800')  # 30 minutes in seconds
    variable_pressure_delay = StringProperty('3600')  # 1 hour in seconds
    zero_pressure_delay = StringProperty('3600')  # 1 hour in seconds

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.intervals = {
            'shutdown_time': 4320,  # 72 hours
            'vac_pump_fault_count': 10,
            'high_pressure_delay': 1800,
            'low_pressure_delay': 1800,
            'variable_pressure_delay': 3600,
            'zero_pressure_delay': 3600
        }
        
    def return_to_main(self):
        '''Return to the main screen'''
        self.app.root.current = 'main'

    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        - Check profile access unless in admin mode
        - Update all option displays.
        '''
        # Skip profile check if in admin mode
        if self.app.admin_mode:
            self._update_displays()
            return
            
        # Check if current profile is CS8
        if self.app.profile != 'CS8':
            # Show access denied message
            dialog = CustomDialog()
            title = self.app.language_handler.translate('access_denied', 'Access Denied')
            text = self.app.language_handler.translate(
                'profile_access_denied',
                'This screen is only available for CS8 profile or with admin access.'
            )
            accept = self.app.language_handler.translate('accept', 'Accept')
            
            dialog.open_dialog(
                title=title,
                text=text,
                accept=accept,
                accept_method=self.return_to_main
            )
            return
            
        self._update_displays()
        
    def _update_displays(self):
        '''Update all option displays'''
    def _update_displays(self):
        '''Update all option displays'''
        # Update the shutdown time display
        if self.app.test_shutdown_time:
            self.shutdown_time = str(self.app.modified_shutdown_time)
        else:
            self.shutdown_time = '4320'  # Default 72 hours
            
        # Update vac pump fault count display
        self.vac_pump_fault_count = self.app.vac_failure_limit_string
        
        # Load current alarm delay settings from alarm manager
        for alarm in self.app.alarm_manager.alarms:
            if alarm.name == 'over_pressure':
                self.high_pressure_delay = str(int(alarm.duration))
            elif alarm.name == 'under_pressure':
                self.low_pressure_delay = str(int(alarm.duration))
            elif alarm.name == 'variable_pressure':
                self.variable_pressure_delay = str(int(alarm.duration))
            elif alarm.name == 'zero_pressure':
                self.zero_pressure_delay = str(int(alarm.duration))

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
        elif caller == 'vac_pump_fault_count':
            self.input_string = self.vac_pump_fault_count
        elif caller == 'high_pressure_delay':
            self.input_string = self.high_pressure_delay
        elif caller == 'low_pressure_delay':
            self.input_string = self.low_pressure_delay
        elif caller == 'variable_pressure_delay':
            self.input_string = self.variable_pressure_delay
        elif caller == 'zero_pressure_delay':
            self.input_string = self.zero_pressure_delay
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
        elif self.current_interval_name == 'vac_pump_fault_count':
            self.ids.input_field.text = self.input_string
        elif self.current_interval_name in ['high_pressure_delay', 'low_pressure_delay',
                                           'variable_pressure_delay', 'zero_pressure_delay']:
            self.ids.input_field.text = f"{self.input_string} sec"
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
        text_start = self.app.language_handler.translate('confirm_interval_change_message',
                                                       'Are you sure you want to modify the system default interval?')
        text_end = self.app.language_handler.translate('dialog_confirmation',
                                                     "Click 'Accept' to confirm or 'Cancel' to return.")

        current_value = ''
        new_value = ''

        if self.current_interval_name == 'shutdown_time':
            current_value = f'4320 min (72 hours)'
            new_value = f'{self.new_interval} min'
        elif self.current_interval_name == 'vac_pump_fault_count':
            current_value = '10'
            new_value = f'{self.new_interval}'
        elif self.current_interval_name == 'high_pressure_delay':
            current_value = '1800 sec (30 min)'
            new_value = f'{self.new_interval} sec'
        elif self.current_interval_name == 'low_pressure_delay':
            current_value = '1800 sec (30 min)'
            new_value = f'{self.new_interval} sec'
        elif self.current_interval_name == 'variable_pressure_delay':
            current_value = '3600 sec (1 hour)'
            new_value = f'{self.new_interval} sec'
        elif self.current_interval_name == 'zero_pressure_delay':
            current_value = '3600 sec (1 hour)'
            new_value = f'{self.new_interval} sec'

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
        value = int(self.input_string)
        
        if self.current_interval_name == 'shutdown_time':
            # Call the app's method to set the test shutdown time
            self.app.set_test_shutdown_time(value)
            
            # Update our local property for UI display
            self.shutdown_time = str(value)
            
            pass
            
            # Mark as user-defined if not default
            if value != 4320:  # 4320 minutes = 72 hours (default)
                self.app.user_defined_change()
                
        elif self.current_interval_name == 'vac_pump_fault_count':
            # Update the app's vac failure limit
            self.app.vac_failure_limit_string = str(value)
            
            # Update our local property for UI display
            self.vac_pump_fault_count = str(value)
            
            # Save to database
            self.app.thresholds_db.add_setting('vac_pump_fault_count', value)
            
            pass
            
            # Mark as user-defined if not default
            if value != 10:
                self.app.user_defined_change()
                
            # Force reload of alarm settings to apply new threshold
            self.app.alarm_manager.check_alarms()
                
        elif self.current_interval_name == 'high_pressure_delay':
            # Update high pressure delay
            self.high_pressure_delay = str(value)
            # Find and update the alarm duration
            for alarm in self.app.alarm_manager.alarms:
                if alarm.name == 'over_pressure':
                    alarm.duration = float(value)
                    break
            pass
            # Mark as user-defined if not default
            if value != 1800:  # 30 minutes
                self.app.user_defined_change()
                
        elif self.current_interval_name == 'low_pressure_delay':
            # Update low pressure delay
            self.low_pressure_delay = str(value)
            # Find and update the alarm duration
            for alarm in self.app.alarm_manager.alarms:
                if alarm.name == 'under_pressure':
                    alarm.duration = float(value)
                    break
            pass
            # Mark as user-defined if not default
            if value != 1800:  # 30 minutes
                self.app.user_defined_change()
                
        elif self.current_interval_name == 'variable_pressure_delay':
            # Update variable pressure delay
            self.variable_pressure_delay = str(value)
            # Find and update the alarm duration
            for alarm in self.app.alarm_manager.alarms:
                if alarm.name == 'variable_pressure':
                    alarm.duration = float(value)
                    break
            pass
            # Mark as user-defined if not default
            if value != 3600:  # 60 minutes
                self.app.user_defined_change()
                
        elif self.current_interval_name == 'zero_pressure_delay':
            # Update zero pressure delay
            self.zero_pressure_delay = str(value)
            # Find and update the alarm duration
            for alarm in self.app.alarm_manager.alarms:
                if alarm.name == 'zero_pressure':
                    alarm.duration = float(value)
                    break
            pass
            # Mark as user-defined if not default
            if value != 3600:  # 60 minutes
                self.app.user_defined_change()
        
        # Force an immediate alarm check to apply the new delay
        self.app.alarm_manager.check_alarms()
        
        self.new_interval = 0
        self.current_sheet.set_state('toggle')

    def default_all(self):
        '''
        Reset all settings to default values.
        '''
        # Show confirmation dialog
        dialog = CustomDialog()
        title = self.app.language_handler.translate('confirm_default_all', 'Confirm Reset to Defaults?')
        text = self.app.language_handler.translate('confirm_default_all_message',
                                                 'Are you sure you want to reset all settings to their default values? '
                                                 'This will reset the theme and all adjustment values.')
        text_end = self.app.language_handler.translate('dialog_confirmation',
                                                     "Click 'Accept' to confirm or 'Cancel' to return.")
        
        full_text = f'{text}\n\n{text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')

        dialog.open_dialog(
            title=title,
            text=full_text,
            accept=accept,
            accept_method=self.confirm_default_all,
            cancel=cancel
        )

    def confirm_default_all(self):
        '''
        Confirm resetting all settings to default values.
        '''
        # Reset the shutdown time
        self.app.reset_test_shutdown_time()
        
        # Reset the vac pump fault count
        self.app.vac_failure_limit_string = '10'
        self.app.thresholds_db.add_setting('vac_pump_fault_count', 10)
        self.vac_pump_fault_count = '10'
        
        # Reset the high pressure delay
        self.app.thresholds_db.add_setting('high_pressure_delay', 1800)
        self.high_pressure_delay = '1800'
        
        # Reset the low pressure delay
        self.app.thresholds_db.add_setting('low_pressure_delay', 1800)
        self.low_pressure_delay = '1800'
        
        # Reset the variable pressure delay
        self.app.thresholds_db.add_setting('variable_pressure_delay', 3600)
        self.variable_pressure_delay = '3600'
        
        # Reset the zero pressure delay
        self.app.thresholds_db.add_setting('zero_pressure_delay', 3600)
        self.zero_pressure_delay = '3600'
        
        # Reset the theme and other defaults
        self.app.default_all()
        
        # Update our local property for UI display
        self.shutdown_time = '4320'  # 72 hours
        
        pass
        
        # Reload alarm settings to apply changes immediately
        self.app.send_reload_signal()