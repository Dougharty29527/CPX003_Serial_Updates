'''
Pressure Calibration Screen
'''

# Kivy imports.
from kivy.properties import BooleanProperty

# Local imports.
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER
from components import CustomDialog, ConfirmationDialog


class PressureCalibrationScreen(BaseOOBEScreen):
    '''
    Pressure Calibration Screen:
    - This screen allows the user to calibrate the pressure sensor during OOBE.
    - It uses the same calibration logic as the main app.
    - The continue button is disabled until the calibration is completed.
    '''

    calibration_completed = BooleanProperty(False)
    continue_enabled = BooleanProperty(False)

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = app.language_handler.translate('pressure_calibration_title', 'PRESSURE CALIBRATION')
        
    def update_translations(self):
        '''
        Update all translatable text elements.
        '''
        # Safety check to ensure app is available
        if not hasattr(self, 'app') or not self.app:
            return
            
        # Update title
        if hasattr(self.ids, 'pressure_calibration_title'):
            self.ids.pressure_calibration_title.text = self.app.language_handler.translate(
                'pressure_calibration_title', 'PRESSURE CALIBRATION'
            )
        
        # Update description lines
        if hasattr(self.ids, 'calibration_description_line1'):
            self.ids.calibration_description_line1.text = self.app.language_handler.translate(
                'pressure_calibration_description_line1', "When you're ready to calibrate the pressure sensor,"
            )
            
        if hasattr(self.ids, 'calibration_description_line2'):
            self.ids.calibration_description_line2.text = self.app.language_handler.translate(
                'pressure_calibration_description_line2', 'press the Calibrate button below.'
            )
            
        # Update calibrate button
        if hasattr(self.ids, 'calibrate_btn'):
            self.ids.calibrate_btn.text = self.app.language_handler.translate('calibrate', 'CALIBRATE')

    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        Preserve completion status if already completed.
        '''
        self.app.stop_any_cycle()
        
        # Update translations when entering the screen
        self.update_translations()
        
        # Check if calibration was already completed
        already_completed = self.app.oobe_db.get_setting('pressure_calibration_completed', 'false') == 'true'
        
        if already_completed:
            # If already completed, set the UI state to completed
            self.calibration_completed = True
            self.continue_enabled = True
            # You could add UI feedback here to show that calibration was already completed
        else:
            # Otherwise, reset the calibration_completed flag to false
            self.calibration_completed = False
            self.continue_enabled = False

    def show_calibration_dialog(self):
        '''
        Show confirmation pop up for pressure calibration.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('calibrate_pressure_sensor', 'Calibrate Pressure Sensor')
        warning = self.app.language_handler.translate('pressure_calibration_warning', 'WARNING:\nThe pressure sensor must be open to atmospheric air\nin order to calibrate!')
        confirmation = self.app.language_handler.translate('calibration_confirmation', 'PRESS CONFIRM WHEN READY, OR CANCEL TO EXIT.')
        text = f'{warning}\n\n{confirmation}'
        accept = self.app.language_handler.translate('confirm', 'Confirm').upper()
        cancel = self.app.language_handler.translate('cancel', 'Cancel')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.calibrate_pressure,
            cancel=cancel
        )

    def calibrate_pressure(self):
        '''
        Calibrate the pressure sensor and show completion dialog when done.
        '''
        # Call the same calibration method used in the main app
        self.app.io.pressure_sensor.calibrate()
        
        # Mark calibration as completed
        self.calibration_completed = True
        
        # Show completion dialog
        self.show_completion_dialog()

    def show_completion_dialog(self):
        '''
        Show the completion dialog box.
        '''
        dialog = ConfirmationDialog()
        title = self.app.language_handler.translate('calibration_complete', 'Calibration Complete')
        text = self.app.language_handler.translate(
            'pressure_calibration_confirmation', 'The pressure sensor has been successfully calibrated.'
        )
        accept = self.app.language_handler.translate('continue', 'CONTINUE')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self._mark_complete_and_go_next
        )

    def on_continue(self):
        '''
        Handle continue button press.
        '''
        if self.calibration_completed:
            # Navigate to the next screen
            self._go_to_next_screen()

    def _mark_complete_and_go_next(self):
        '''
        Mark the calibration as complete and navigate to the next screen.
        This is called when the user clicks the accept button in the completion dialog.
        '''
        # Set the flag in the database only when user confirms completion
        self.app.oobe_db.add_setting('pressure_calibration_completed', 'true')
        
        # Navigate to the next screen
        self._go_to_next_screen()
    
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
    
    def go_back(self):
        '''
        Go back to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)