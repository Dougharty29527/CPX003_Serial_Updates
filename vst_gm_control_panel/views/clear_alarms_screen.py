'''
Clear Alarms Screen
'''

# Standard imports.
from datetime import datetime

# Kivy imports.
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty

# Local imports.
from components import CustomDialog

class ClearAlarmsScreen(MDScreen):
    '''
    Clear Alarms Screen:
    - This class sets up the Clear Alarms Screen.
    '''

    selected_alarm = StringProperty('')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.alarms = {
            'overfill',
            'vac_pump',
            'under_pressure',
            'over_pressure',
            'variable_pressure',
            'zero_pressure'
        }

    def clear_alarm(self):
        '''
        Clear the selected alarm.
        '''
        self.selected_alarm = self.selected_alarm.lower().replace(' ', '_')
        alarm_settings = {
            'variable_pressure': 'variable_pressure_point',
            'vac_pump': 'vac_pump_failure_count',
            'overfill': 'last_overfill_time'
        }
        # Clear specific alarm settings, if they exist.
        if self.selected_alarm in alarm_settings:
            self.app.alarms_db.add_setting(alarm_settings[self.selected_alarm], None)
        # Clear general alarm settings.
        self.app.gm_db.add_setting(f'{self.selected_alarm}_alarm', None)
        self.app.alarms_db.add_setting(f'{self.selected_alarm}_start_time', None)
        
        # Turn shutdown relay back on when alarm is cleared
        self.app.io.set_shutdown_relay(True)
        
        pass
        
        # Check if we need to exit shutdown mode
        if self.app.shutdown:
            self.app.toggle_shutdown(False)
        
        # Send reload signal to refresh alarm state
        self.app.send_reload_signal()
        
        # Reset the selected alarm.
        self.selected_alarm = ''

    def show_dialog(self, caller):
        '''
        Show confirmation pop up.
        '''
        translations = {
            'title': ('confirm_alarm_clear', 'Clear Alarm?'),
            'text_start': ('confirm_alarm_clear_message', 'Are you sure you want to reset the alarm condition and duration?'),
            'text_end': ('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return."),
            'accept': ('accept', 'Accept'),
            'cancel': ('cancel', 'Cancel')
        }
        if caller in self.alarms:
            self.selected_alarm = caller
            self.selected_alarm = self.app.language_handler.translate(caller, caller.upper())
            dialog = CustomDialog()

            title = self.app.language_handler.translate(*translations['title'])

            text_start = self.app.language_handler.translate(*translations['text_start'])
            text_end = self.app.language_handler.translate(*translations['text_end'])
            text = f'{text_start}\n{self.selected_alarm}\n\n{text_end}'

            accept = self.app.language_handler.translate(*translations['accept'])
            cancel = self.app.language_handler.translate(*translations['cancel'])

            dialog.open_dialog(
                title=title,
                text=text,
                accept=accept,
                accept_method=self.clear_alarm,
                cancel=cancel
            )