'''
Functionality Test Screen
'''

# Standard imports.
import threading

# Kivy imports.
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty

# Local imports.
from components import ConfirmationDialog, CustomDialog


class FunctionalityTestScreen(MDScreen):
    '''
    Functionality Test Screen:
    - This class sets up the Functionality Test Screen.
    '''

    time_display = StringProperty('10:00')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.elapsed = 0
        self.total_seconds = 60 * 10

    def on_enter(self):
        '''
        Set the timers to default values.
        '''
        self.app.stop_any_cycle()
        self.reset_timers()

    def reset_timers(self):
        '''
        Reset the countdown timer.
        '''
        self.elapsed = 0

        if self.app.debug:
            self.total_seconds = 60
            self.time_display = '01:00'
        else:
            self.total_seconds = 60 * 10
            self.time_display = '10:00'

    def start_functionality_test(self):
        '''
        Begin the functionality test.
        '''
        conditions = self.app.check_cycle_conditions('functionality_test')

        if not conditions:
            self.app.toggle_functionality_test(True)
            self.start_countdown()
            Clock.schedule_interval(self.check_conditions, 1)
        else:
            self.show_alarm_dialog()

    def stop_functionality_test(self):
        '''
        Stop the functionality test.
        '''
        self.app.toggle_functionality_test(False)
        self.unschedule_all(self)
        self.show_completion_dialog()

    def check_conditions(self, *args):
        '''
        Check the conditions for the functionality test.
        '''
        conditions = self.app.check_cycle_conditions('functionality_test')
        if conditions:
            self.stop_functionality_test()
            self.show_alarm_dialog()

    def unschedule_all(self, *args):
        '''
        Unschedule all the timers.
        '''
        Clock.unschedule(self.update_time)
        Clock.unschedule(self.check_conditions)

    def start_countdown(self):
        '''
        Start the countdown timer.
        '''
        Clock.schedule_interval(self.update_time, 1)

    def update_time(self, dt):
        '''
        Update the countdown timer.
        '''
        if self.total_seconds > 0:
            self.total_seconds -= 1
            self.elapsed += 1
            minutes, seconds = divmod(self.total_seconds, 60)
            self.time_display = f'{minutes:02}:{seconds:02}'
        else:
            self.stop_functionality_test()

    def show_completion_dialog(self):
        '''
        Show the dialog box.
        '''
        dialog = ConfirmationDialog()
        title = self.app.language_handler.translate('test_complete', 'Test Complete')
        text_start = self.app.language_handler.translate(
            'functionality_test_confirmation', 'The functionality test has finished successfully.'
        )
        minutes, seconds = divmod(self.elapsed, 60)
        duration = f'{minutes:02}:{seconds:02}'
        total_duration = self.app.language_handler.translate('total_duration', 'Total Duration')
        duration_str = f'{total_duration}: {duration}'
        text = f'{text_start}\n\n{duration_str}'
        accept = 'OK'

        if self.app.language == 'ES':
            accept = self.app.language_handler.translate('accept', 'Aceptar')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept
        )

        self.reset_timers()

    def show_alarm_dialog(self):
        '''
        Show the dialog box.
        '''
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

    def confirm_functionality_test(self):
        '''
        Confirmation popup.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('start_functionality_test', 'Start Functionality Test?')
        text = self.app.language_handler.translate('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return.")
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.start_functionality_test,
            cancel=cancel
        )