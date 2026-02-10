'''
Overfill Override Screen
'''

# Kivy imports.
from kivymd.uix.screen import MDScreen

# Local imports.
from components import CustomDialog


class OverfillOverrideScreen(MDScreen):
    '''
    This class sets up the Overfill Override Screen.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

    def show_override_dialog(self):
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
        vac_pump_alarm = self.app.language_handler.translate('overfill', 'Overfill')
        dialog = CustomDialog()

        title = self.app.language_handler.translate(*translations['title'])

        text_start = self.app.language_handler.translate(*translations['text_start'])
        text_end = self.app.language_handler.translate(*translations['text_end'])
        text = f'{text_start}\n{vac_pump_alarm}\n\n{text_end}'

        accept = self.app.language_handler.translate(*translations['accept'])
        cancel = self.app.language_handler.translate(*translations['cancel'])

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.clear_overfill,
            cancel=cancel
        )

    def clear_overfill(self):
        '''
        Clear the vacuum pump alarm.
        '''
        self.app.alarms_db.add_setting('overfill_start_time', None)
        self.app.alarms_db.add_setting('last_overfill_time', None)
        self.app.gm_db.add_setting('overfill_alarm', None)