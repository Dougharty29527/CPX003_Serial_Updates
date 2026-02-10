'''
Quick Functionality Test Screen
'''

# Standard imports.
import threading

# Kivy imports.
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty

# Local imports.
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER
from components import ConfirmationDialog, CustomDialog


class QuickFunctionalityTestScreen(BaseOOBEScreen):
    '''
    Quick Functionality Test Screen:
    - This screen allows the user to run a quick functionality test during OOBE.
    - The test alternates between Run and Purge modes every 60 seconds.
    - The test will end after 4 minutes (240 seconds).
    '''

    time_display = StringProperty('04:00')
    test_running = BooleanProperty(False)
    test_completed = BooleanProperty(False)

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = app.language_handler.translate('quick_functionality_test_title', 'QUICK FUNCTIONALITY TEST')
        self.elapsed = 0
        self.total_seconds = 60 * 4  # 4 minutes
        self.cycle_duration = 60  # 60 seconds per cycle
        self.current_cycle = 0
        self.max_cycles = 4  # 4 cycles (run, purge, run, purge)

    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        Reset the timers but preserve completion status if already completed.
        '''
        self.app.stop_any_cycle()
        self.reset_timers()
        
        # Check if the test was already completed
        already_completed = self.app.oobe_db.get_setting('quick_functionality_test_completed', 'false') == 'true'
        
        if already_completed:
            # If already completed, set the UI state to completed
            self.test_completed = True
            # You could add UI feedback here to show that the test was already completed
        else:
            # Otherwise, reset the test_completed flag to false
            self.test_completed = False

    def reset_timers(self):
        '''
        Reset the countdown timer.
        '''
        self.elapsed = 0
        self.total_seconds = 60 * 4  # 4 minutes
        self.time_display = '04:00'
        self.current_cycle = 0
        self.test_running = False

    def start_functionality_test(self):
        '''
        Begin the quick functionality test.
        '''
        conditions = self.app.check_cycle_conditions('functionality_test')

        if not conditions:
            self.test_running = True
            self.app.toggle_functionality_test(True)
            self.start_countdown()
            Clock.schedule_interval(self.check_conditions, 1)
        else:
            self.show_alarm_dialog()

    def stop_functionality_test(self):
        '''
        Stop the quick functionality test.
        '''
        self.test_running = False
        self.app.toggle_functionality_test(False)
        self.unschedule_all()
        
        # Only show completion dialog if test was completed
        if self.elapsed >= self.total_seconds:
            self.test_completed = True
            self.show_completion_dialog()
        else:
            # Reset timers if test was stopped early
            self.reset_timers()
            # Explicitly mark test as incomplete when stopped early
            self.app.oobe_db.add_setting('quick_functionality_test_completed', 'false')

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
        Update the countdown timer and manage cycle transitions.
        '''
        if self.total_seconds > 0:
            self.total_seconds -= 1
            self.elapsed += 1
            minutes, seconds = divmod(self.total_seconds, 60)
            self.time_display = f'{minutes:02}:{seconds:02}'
            
            # Check if we need to switch cycles
            if self.elapsed % self.cycle_duration == 0:
                self.current_cycle += 1
                
                # If we've completed all cycles, stop the test
                if self.current_cycle >= self.max_cycles:
                    self.stop_functionality_test()
        else:
            self.stop_functionality_test()

    def _mark_complete_and_go_next(self):
        '''
        Mark the test as complete and navigate to the next screen.
        This is called when the user clicks the accept button in the completion dialog.
        '''
        # Mark quick functionality test as complete
        self.app.oobe_db.add_setting('quick_functionality_test_completed', 'true')
        
        # Navigate to the next screen
        self._go_to_next_screen()
    
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
    
    def show_completion_dialog(self):
        '''
        Show the dialog box.
        '''
        dialog = ConfirmationDialog()
        title = self.app.language_handler.translate('test_complete', 'Test Complete')
        text_start = self.app.language_handler.translate(
            'quick_functionality_test_confirmation', 'The quick functionality test has finished successfully.'
        )
        minutes, seconds = divmod(self.elapsed, 60)
        duration = f'{minutes:02}:{seconds:02}'
        total_duration = self.app.language_handler.translate('total_duration', 'Total Duration')
        duration_str = f'{total_duration}: {duration}'
        text = f'{text_start}\n\n{duration_str}'
        accept = self.app.language_handler.translate('accept', 'ACCEPT')
        
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self._mark_complete_and_go_next
        )

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
        accept = self.app.language_handler.translate('accept', 'OK')

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
        title = self.app.language_handler.translate('start_quick_functionality_test', 'Start Quick Functionality Test?')
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
        
    def go_back(self):
        '''
        Go back to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)