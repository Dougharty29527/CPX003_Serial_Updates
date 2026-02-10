'''
Efficiency Test Screen
'''

# Standard imports.
import threading

# Kivy imports.
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty

# Local imports.
from components import ConfirmationDialog, CustomDialog


class EfficiencyTestScreen(MDScreen):
    '''
    Efficiency Test Screen:
    - This class sets up the Efficiency Test Screen.
    '''

    time_display = StringProperty('02:00')
    FILL_RUN_TIME = 120  # 2 minutes
    PURGE_TIME = 346    # (50s purge + 5s burp) × 6 + 15s rest = 346s

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.elapsed = 0
        self.total_seconds = self.FILL_RUN_TIME

    def on_enter(self):
        self.app.stop_any_cycle()
        self.reset_timers()

    def reset_timers(self):
        self.elapsed = 0
        self.total_seconds = self.FILL_RUN_TIME
        self.time_display = '02:00'

    def start_fill_run(self):
        conditions = self.app.check_cycle_conditions('efficiency_test')
        if not conditions:
            self.app.efficiency_test = True
            self.app.io.efficiency_test_fill_run()
            # Set timer for fill/run mode
            self.total_seconds = 30 if self.app.debug else self.FILL_RUN_TIME
            minutes, seconds = divmod(self.total_seconds, 60)
            self.time_display = f'{minutes:02}:{seconds:02}'
            self.start_countdown()
            Clock.schedule_interval(self.check_conditions, 1)
        else:
            self.show_alarm_dialog()

    def start_purge(self):
        conditions = self.app.check_cycle_conditions('efficiency_test')
        if not conditions:
            self.app.efficiency_test = True
            self.app.io.efficiency_test_purge()
            # Set timer for purge mode
            self.total_seconds = 30 if self.app.debug else self.PURGE_TIME
            minutes, seconds = divmod(self.total_seconds, 60)
            self.time_display = f'{minutes:02}:{seconds:02}'
            self.start_countdown()
            Clock.schedule_interval(self.check_conditions, 1)
        else:
            self.show_alarm_dialog()

    def stop_efficiency_test(self):
        self.app.efficiency_test = False
        self.app.stop_any_cycle()
        self.unschedule_all()
        self.show_completion_dialog()

    def check_conditions(self, *args):
        conditions = self.app.check_cycle_conditions('efficiency_test')
        if conditions:
            self.stop_efficiency_test()
            self.show_alarm_dialog()

    def unschedule_all(self, *args):
        Clock.unschedule(self.update_time)
        Clock.unschedule(self.check_conditions)

    def start_countdown(self):
        Clock.schedule_interval(self.update_time, 1)

    def update_time(self, dt):
        if self.total_seconds > 0:
            self.total_seconds -= 1
            self.elapsed += 1
            minutes, seconds = divmod(self.total_seconds, 60)
            self.time_display = f'{minutes:02}:{seconds:02}'
        else:
            self.stop_efficiency_test()

    def show_completion_dialog(self):
        '''
        Show the dialog box.
        '''
        dialog = ConfirmationDialog()
        title = self.app.language_handler.translate('test_complete', 'TEST COMPLETE')
        text_start = self.app.language_handler.translate(
            'efficiency_test_confirmation', 'The efficiency test has finished successfully.'
        )
        minutes, seconds = divmod(self.elapsed, 60)
        duration = f'{minutes:02}:{seconds:02}'
        total_duration = self.app.language_handler.translate('total_duration', 'Total Duration')
        duration_str = f'{total_duration}: {duration}'
        text = f'{text_start}\n\n{duration_str}'
        dialog.open_dialog(
            title=title,
            text=text,
            accept='OK'
        )

        self.reset_timers()

    def show_alarm_dialog(self):
        '''
        Show the dialog box.
        '''
        dialog = ConfirmationDialog()
        title = self.app.language_handler.translate('alarm_dialog_title', 'ALARMS DETECTED')
        text_start = self.app.language_handler.translate(
            'alarm_dialog_one', 'Cannot start the test while alarms are active.'
        )
        text_end = self.app.language_handler.translate(
            'alarm_dialog_two', 'Please acknowledge or resolve all alarms before proceeding.'
        )
        text = f'{text_start}\n\n{text_end}'
        dialog.open_dialog(
            title=title,
            text=text,
            accept='OK'
        )

    def confirm_fill_run(self):
        '''
        Confirmation popup for fill/run.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('start_fill_run_title', 'START FILL/RUN CYCLE?')
        text = self.app.language_handler.translate('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return.")
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.start_fill_run,
            cancel=cancel
        )

    def confirm_purge(self):
        '''
        Confirmation popup for purge.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('start_purge_title', 'START PURGE CYCLE?')
        text = self.app.language_handler.translate('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return.")
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.start_purge,
            cancel=cancel
        )