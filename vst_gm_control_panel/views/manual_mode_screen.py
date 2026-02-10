'''
Manual Mode Screen
'''

# Standard imports
import time

# Kivy imports
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty
from kivy.logger import Logger
from kivymd.uix.screen import MDScreen

# Local imports
from components import ConfirmationDialog, CustomDialog


class ManualModeScreen(MDScreen):
    '''
    Manual Mode Screen.
    '''

    current_manual_cycle_count = StringProperty('0')
    manual_mode_running = BooleanProperty(False)

    # Relay states.
    motor = BooleanProperty(False)
    v1 = BooleanProperty(False)
    v2 = BooleanProperty(False)
    v5 = BooleanProperty(False)

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.get_manual_cycle_count()
        self.last_relays = ''
        self.start_time = None
        self.manual_cycle_counter = 0

    def _update_button_states(self, start_disabled, stop_disabled):
        '''
        Update the start/stop button states.
        '''
        self.ids.start.disabled = start_disabled
        self.ids.stop.disabled = stop_disabled

    def start_manual_cycle(self):
        '''
        Begin the Manual Mode Cycle - simplified version based on working 0.4.10.
        '''
        Logger.info('ManualModeScreen: Starting Manual Mode Cycle')
        self.manual_cycle_counter = 0
        self.start_time = time.time()
        self.app.toggle_manual_mode(True)
        self._update_button_states(start_disabled=True, stop_disabled=False)
        Clock.schedule_interval(self.get_active_relays, 1)
        Clock.schedule_interval(self.run_manual_mode, 1)
        Clock.schedule_interval(self.check_conditions, 1)

    def run_manual_mode(self, *args):
        '''
        Execute the Manual Mode Cycle - simplified version based on working 0.4.10.
        '''
        if self.manual_cycle_counter > 3:
            self.stop_manual_cycle()
            return

        elif self.manual_cycle_counter < 4:
            if self.app.io.cycle_process is not None and self.app.io.cycle_process.is_alive():
                return
            else:
                self.app.toggle_manual_mode(True)
                self.update_manual_cycle_count()
                if self.manual_cycle_counter <= 3:
                    self.manual_cycle_counter += 1
                Logger.info(f'ManualModeScreen: Running Manual Mode Cycle Count: {self.manual_cycle_counter}')
                time.sleep(.1)
                self.app.io.manual_mode()

    def stop_manual_cycle(self):
        '''
        Stop the Manual Mode Cycle - simplified version based on working 0.4.10.
        '''
        Logger.info('ManualModeScreen: Stopping Manual Mode Cycle')
        self.app.stop_any_cycle()
        self.unschedule_all(self)
        self.app.io.set_rest()
        self.last_relays = ''
        self.motor = False
        self.v1 = False
        self.v2 = False
        self.v5 = False
        self.start_time = None
        self._update_button_states(start_disabled=False, stop_disabled=True)
        self.app.toggle_manual_mode(False)


    def get_manual_cycle_count(self):
        '''
        Get the current manual mode run cycle count - simplified version based on working 0.4.10.
        '''
        try:
            manual_cycles = self.app.gm_db.get_setting('manual_cycle_count')
        except Exception as e:
            manual_cycles = 0
        if manual_cycles:
            self.current_manual_cycle_count = (manual_cycles)
        else:
            self.current_manual_cycle_count = '0'

    def update_manual_cycle_count(self):
        '''
        Update the manual cycle count - simplified version based on working 0.4.10.
        '''
        manual_cycles = int(self.current_manual_cycle_count)
        manual_cycles += 1
        self.current_manual_cycle_count = str(manual_cycles)
        try:
            self.app.gm_db.add_setting('manual_cycle_count', manual_cycles)
        except Exception as e:
            print(f'Error updating manual cycle count: {e}')

    def unschedule_all(self, *args):
        '''
        Unschedule all the timers - simplified version based on working 0.4.10.
        '''
        Clock.unschedule(self.check_conditions)
        Clock.unschedule(self.run_manual_mode)
        Clock.unschedule(self.get_active_relays)
        self.app.io.set_rest()

    def check_conditions(self, *args):
        '''
        Check the conditions for the manual mode - simplified version based on working 0.4.10.
        '''
        conditions = self.app.check_cycle_conditions('manual_mode')
        if conditions:
            self.stop_manual_cycle()
            if self.app.alarm:
                self.show_alarm_dialog()


    def get_active_relays(self, *args):
        '''
        Get the active relays and update their states using ultra-fast memory-mapped file (replaces database).
        '''
        current_relays = self.app.io.mode_manager.get_mode()
        if current_relays:
            self.app.active_relays = current_relays
        else:
            self.app.active_relays = 'rest'

        # Check if the relays string has changed.
        if current_relays == self.last_relays:
            return  # No changes, so no need to update.

        # Update the last known relays.
        self.last_relays = current_relays

        if current_relays == 'run':
            states = {'motor': True, 'v1': True, 'v2': False, 'v5': True}
        elif current_relays == 'purge':
            states = {'motor': True, 'v1': False, 'v2': True, 'v5': False}
        elif current_relays == 'burp':
            states = {'motor': False, 'v1': False, 'v2': False, 'v5': True}
        else:
            states = {'motor': False, 'v1': False, 'v2': False, 'v5': False}

        for attr, value in states.items():
            setattr(self, attr, value)

    def confirm_manual_mode(self):
        '''
        Confirmation popup - simplified version based on working 0.4.10.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('start_manual_mode', 'Start Manual Mode?')
        text = self.app.language_handler.translate('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return.")
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.start_manual_cycle,
            cancel=cancel
        )

    def show_alarm_dialog(self):
        '''
        Show the dialog box - simplified version based on working 0.4.10.
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