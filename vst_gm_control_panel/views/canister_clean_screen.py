'''
Canister Clean Screen
'''

# Standard imports.
import threading

# Kivy imports.
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty
from kivy.logger import Logger

# Local imports.
from components import ConfirmationDialog, CustomDialog


class CanisterCleanScreen(MDScreen):
    '''
    Canister Clean Screen:
    - This class sets up the Canister Clean Screen.
    '''

    time_display = StringProperty('02:00:00')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.elapsed = 0
        self.total_seconds = 7200  # 2 hours

    def on_enter(self):
        self.app.stop_any_cycle()
        self.reset_timers()

    def reset_timers(self):
        self.elapsed = 0
        self.total_seconds = 7200
        self.time_display = '02:00:00'

    def start_canister_clean(self):
        conditions = self.app.check_cycle_conditions('canister_clean')
        if not conditions:
            self.app.canister_clean = True
            self.app.io.canister_clean()
            Logger.info('Canister Clean: Canister clean started.')
            self.start_countdown()
            Clock.schedule_interval(self.check_conditions, 1)
        else:
            self.show_alarm_dialog()

    def stop_canister_clean(self):
        self.app.canister_clean = False
        self.app.stop_any_cycle()
        self.unschedule_all()
        Logger.info('Canister Clean: Canister clean stopped.')
        self.show_completion_dialog()

    def check_conditions(self, *args):
        conditions = self.app.check_cycle_conditions('canister_clean')
        if conditions:
            self.stop_canister_clean()
            self.show_alarm_dialog()
            Logger.info('Canister Clean: Alarms detected, stopping canister clean.')

    def unschedule_all(self, *args):
        Clock.unschedule(self.update_time)
        Clock.unschedule(self.check_conditions)

    def start_countdown(self):
        Clock.schedule_interval(self.update_time, 1)

    def update_time(self, dt):
        if self.total_seconds > 0:
            self.total_seconds -= 1
            self.elapsed += 1
            hours, remainder = divmod(self.total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.time_display = f'{hours:02}:{minutes:02}:{seconds:02}'
        else:
            self.stop_canister_clean()

    def show_completion_dialog(self):
        '''
        Show the dialog box.
        '''
        dialog = ConfirmationDialog()
        title = self.app.language_handler.translate('test_complete', 'TEST COMPLETE')
        text_start = self.app.language_handler.translate(
            'clean_canister_confirmation', 'The canister clean has finished successfully.'
        )
        hours, remainder = divmod(self.elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration = f'{hours:02}:{minutes:02}:{seconds:02}'
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

    def show_canister_clean_warning(self):
        '''
        Show warning dialog before starting canister clean.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('start_clean_canister', 'START CANISTER CLEAN?')
        warning = self.app.language_handler.translate('canister_clean_warning', 'WARNING: To clean the canisters, the vapor inlet line should be closed using the ball valve and the cap on the pipe tee should be removed. If this procedure isn\'t done properly it will damage the system')
        confirmation = self.app.language_handler.translate('canister_clean_confirmation', 'PRESS CONFIRM WHEN READY, OR CANCEL TO EXIT.')
        text = f'{warning}\n\n{confirmation}'
        accept = self.app.language_handler.translate('confirm', 'Confirm').upper()
        cancel = self.app.language_handler.translate('cancel', 'Cancel')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.confirm_canister_clean,
            cancel=cancel
        )

    def confirm_canister_clean(self):
        '''
        Confirmation popup after warning dialog.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('start_clean_canister', 'START CANISTER CLEAN?')
        text = self.app.language_handler.translate('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return.")
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.start_canister_clean,
            cancel=cancel
        )