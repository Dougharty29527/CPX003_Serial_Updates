'''
OOBE Overfill Override Screen
'''

# Standard imports
from datetime import datetime, timedelta

# Kivy imports.
from kivy.properties import BooleanProperty
from kivy.clock import Clock

# Local imports.
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER
from components import CustomDialog, ConfirmationDialog


class OOBEOverfillOverrideScreen(BaseOOBEScreen):
    '''
    OOBE Overfill Override Screen:
    - This screen allows the user to configure the N.C. output relay in the tank monitoring system.
    - The "Confirm Override" button is disabled until there's an overfill alarm.
    - When clicked, it shows a popup similar to the existing overfill override functionality.
    - Accepting the popup clears the overfill alarm and marks this part of the OOBE as complete.
    '''

    override_completed = BooleanProperty(False)
    continue_enabled = BooleanProperty(False)
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = app.language_handler.translate('overfill_override_title', 'OVERFILL OVERRIDE')
        self.alarm_check_event = None
        
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        Preserve completion status if already completed.
        '''
        self.app.stop_any_cycle()
        
        # Check if override was already completed
        already_completed = self.app.oobe_db.get_setting('overfill_override_completed', 'false') == 'true'
        
        if already_completed:
            # If already completed, set the UI state to completed
            self.override_completed = True
            self.continue_enabled = True
            # You could add UI feedback here to show that override was already completed
        else:
            # Otherwise, reset the override_completed flag to false
            self.override_completed = False
            self.continue_enabled = False
        
        # Get a reference to the button
        confirm_button = self.ids.get('confirm_override', None)
        
        # Forcefully disable the button initially
        if confirm_button:
            confirm_button.disabled = True
            # Make the button completely non-functional initially
            self._original_on_press = confirm_button.on_press
            confirm_button.on_press = lambda: None
        
        # Check if there's an overfill alarm and enable the button if there is
        self._check_overfill_alarm()
        
        # Start continuous checking for overfill alarm status
        self._start_alarm_monitoring()
        
    def _check_overfill_alarm(self):
        '''
        Check if there's an overfill alarm and enable the button if there is.
        Only checks for an active overfill alarm, not the TLS pin status.
        '''
        # Check for an active overfill alarm
        current_time = datetime.now()
        
        # Check if there's an active overfill alarm (within 2 hours)
        last_overfill_time = self.app.alarms_db.get_setting('last_overfill_time', None)
        alarm_active = False
        
        if last_overfill_time and last_overfill_time != 'None':
            try:
                overfill_time = datetime.fromisoformat(last_overfill_time)
                alarm_active = (current_time - overfill_time) < timedelta(hours=2)
            except (ValueError, TypeError):
                # Handle invalid datetime format
                alarm_active = False
        
        # Set the continue_enabled property based on the alarm status
        self.continue_enabled = alarm_active
        
        # FORCEFULLY disable the button if there's no active alarm
        confirm_button = self.ids.get('confirm_override', None)
        if confirm_button:
            confirm_button.disabled = not alarm_active
            # Extra safety: if no alarm, make the button completely non-functional
            if not alarm_active:
                confirm_button.on_press = lambda: None
            else:
                # Restore the original on_press handler if alarm is active
                if hasattr(self, '_original_on_press') and self._original_on_press:
                    confirm_button.on_press = self._original_on_press
                else:
                    confirm_button.on_press = self.show_override_dialog
        
    def show_override_dialog(self):
        '''
        Show confirmation pop up for overfill override.
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
        Clear the overfill alarm and show completion dialog.
        '''
        # Clear the overfill alarm
        # In a real implementation, this would use the same logic as the main app
        self.app.alarms_db.add_setting('overfill_start_time', None)
        self.app.alarms_db.add_setting('last_overfill_time', None)
        self.app.gm_db.add_setting('overfill_alarm', None)
        
        # Mark override as completed
        self.override_completed = True
        
        # Show completion dialog
        self.show_completion_dialog()
        
    def show_completion_dialog(self):
        '''
        Show the completion dialog box.
        '''
        dialog = ConfirmationDialog()
        title = self.app.language_handler.translate('override_complete', 'Override Complete')
        text = self.app.language_handler.translate(
            'overfill_override_confirmation', 'The overfill alarm has been successfully cleared.'
        )
        accept = self.app.language_handler.translate('continue', 'CONTINUE')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self._mark_complete_and_go_next
        )
        
    def _mark_complete_and_go_next(self):
        '''
        Mark the override as complete and navigate to the next screen.
        This is called when the user clicks the accept button in the completion dialog.
        '''
        # Set the flag in the database only when user confirms completion
        self.app.oobe_db.add_setting('overfill_override_completed', 'true')
        
        # Navigate to the next screen
        self._go_to_next_screen()
    
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
    
    def _start_alarm_monitoring(self):
        '''
        Start periodic checking for overfill alarm status.
        '''
        # Schedule the alarm check to run every second
        self.alarm_check_event = Clock.schedule_interval(
            lambda dt: self._check_overfill_alarm(), 1.0
        )
    
    def _stop_alarm_monitoring(self):
        '''
        Stop periodic checking for overfill alarm status.
        '''
        if self.alarm_check_event:
            self.alarm_check_event.cancel()
            self.alarm_check_event = None
    
    def on_leave(self):
        '''
        Called when leaving the screen.
        Stop the alarm monitoring.
        '''
        self._stop_alarm_monitoring()
        
    def go_back(self):
        '''
        Go back to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        # Stop alarm monitoring before navigating away
        self._stop_alarm_monitoring()
        
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)