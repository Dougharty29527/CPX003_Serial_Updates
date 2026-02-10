'''
Startup Code Screen
'''

# Standard imports
import subprocess
from datetime import datetime

# Kivy imports
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER
from components import CustomDialog


class StartupCodeScreen(BaseOOBEScreen):
    '''
    Startup Code Screen:
    - This screen allows the user to enter the startup code.
    - The code must match the last 6 digits of the Raspberry Pi's serial number.
    - If valid, the startup code is stored in the GM database and the OOBE step is marked as complete.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = app.language_handler.translate('startup_code_title', 'STARTUP CODE')
        self.startup_code = ""
        
        # Directly add translations to the database
        self._add_translations_directly()
        
    def _add_translations_directly(self):
        '''
        Directly add translations to the database to ensure they are available.
        '''
        try:
            # English translations
            english_translations = {
                'startup_code_title': 'STARTUP CODE',
                'startup_code_description_line1': 'GO TO WWW.VSTHOSE.COM AND COMPLETE APPENDIX B',
                'startup_code_description_line2': 'AS YOU WALK THROUGH THIS SETUP.',
                'startup_code_empty_error': 'Startup code cannot be empty',
                'startup_code_invalid_error': 'Invalid startup code',
                'startup_code_success_title': 'Success',
                'startup_code_success_message': 'Startup code verified successfully.',
                'confirm': 'CONFIRM',
                'continue': 'CONTINUE',
            }
            
            # Spanish translations
            spanish_translations = {
                'startup_code_title': 'CÓDIGO DE INICIO',
                'startup_code_description_line1': 'VAYA A WWW.VSTHOSE.COM Y COMPLETE EL APÉNDICE B',
                'startup_code_description_line2': 'MIENTRAS REALIZA ESTA CONFIGURACIÓN.',
                'startup_code_empty_error': 'El código de inicio no puede estar vacío',
                'startup_code_invalid_error': 'Código de inicio inválido',
                'startup_code_success_title': 'Éxito',
                'startup_code_success_message': 'Código de inicio verificado con éxito.',
                'confirm': 'CONFIRMAR',
                'continue': 'CONTINUAR',
            }
            
            # Add English translations
            for key, value in english_translations.items():
                self.app.translations_db.add_translation('EN', key, value)
            
            # Add Spanish translations
            for key, value in spanish_translations.items():
                self.app.translations_db.add_translation('ES', key, value)
                
        except Exception as e:
            pass
    
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        Reset the input field but preserve completion status.
        '''
        self.app.stop_any_cycle()
        self.ids.code_input.text = ""
        
        # Add translations directly to ensure they are available
        self._add_translations_directly()
        
        # Update all text elements with current language translations
        self._update_translations()
        
        # Check if the startup code was already entered
        already_completed = self.app.oobe_db.get_setting('startup_code_entered', 'false') == 'true'
        
        # If already completed, enable the continue button or show a message
        if already_completed:
            # You could add UI feedback here to show that the code was already entered
            pass
            
    def _update_translations(self):
        '''
        Update all text elements with current language translations.
        '''
        try:
            # Update screen title
            self.screen_title = self.app.language_handler.translate('startup_code_title', 'STARTUP CODE')
            
            # Update UI elements
            if hasattr(self.ids, 'startup_code_title'):
                self.ids.startup_code_title.text = self.app.language_handler.translate('startup_code_title', 'STARTUP CODE')
                
            if hasattr(self.ids, 'startup_code_description_line1'):
                self.ids.startup_code_description_line1.text = self.app.language_handler.translate(
                    'startup_code_description_line1',
                    'GO TO WWW.VSTHOSE.COM AND COMPLETE APPENDIX B'
                )
                
            if hasattr(self.ids, 'startup_code_description_line2'):
                self.ids.startup_code_description_line2.text = self.app.language_handler.translate(
                    'startup_code_description_line2',
                    'AS YOU WALK THROUGH THIS SETUP.'
                )
                
            if hasattr(self.ids, 'confirm_btn'):
                self.ids.confirm_btn.text = self.app.language_handler.translate('confirm', 'CONFIRM')
        except Exception as e:
            pass
        
    def add_character(self, char):
        '''
        Add a character to the input field.
        '''
        current_text = self.ids.code_input.text
        self.ids.code_input.text = current_text + str(char)
        
    def delete_character(self):
        '''
        Remove a character from the input field.
        '''
        current_text = self.ids.code_input.text
        
        if len(current_text) >= 1:
            current_text = current_text[:-1]
            self.ids.code_input.text = current_text
        
    def on_code_entered(self):
        '''
        Handle startup code entry.
        '''
        # Get the code from the text field
        code_field = self.ids.code_input
        self.startup_code = code_field.text.strip()
        
        if not self.startup_code:
            # Show error if code is empty
            code_field.error = True
            code_field.helper_text = self.app.language_handler.translate(
                'startup_code_empty_error', 
                "Startup code cannot be empty"
            )
            return
            
        # Validate the code against the Raspberry Pi serial number
        if self.validate_startup_code():
            # Save the startup code to the database
            self.app.gm_db.add_setting('startup_code', self.startup_code)
            
            # Mark startup code entry as complete
            self.app.oobe_db.add_setting('startup_code_entered', 'true')
            
            # Show success dialog
            self.show_success_dialog()
        else:
            # Show error if code is invalid
            code_field.error = True
            code_field.helper_text = self.app.language_handler.translate(
                'startup_code_invalid_error', 
                "Invalid startup code"
            )
            # Clear the input field
            code_field.text = ""
            
    def validate_startup_code(self):
        '''
        Validate the startup code against the Raspberry Pi serial number or the secret override code.
        The validation is case-insensitive.
        
        Returns:
            bool: True if the code is valid, False otherwise
        '''
        # Check if the code matches the secret override password "C0D3CAF3"
        if self.startup_code.upper() == "C0D3CAF3":
            return True
            
        try:
            # Use the command to get the last 6 digits of the Raspberry Pi serial number
            cmd = "cat /proc/cpuinfo | grep Serial | awk '{print substr($3, length($3)-5)}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # Get the last 6 digits
            last_six = result.stdout.strip()
            
            if not last_six:
                # If we couldn't find the serial number, return False
                return False
                
            # Compare the codes case-insensitively
            return self.startup_code.upper() == last_six.upper()
        except Exception as e:
            return False
            
    def show_success_dialog(self):
        '''
        Show a success dialog when the startup code is valid.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate('startup_code_success_title', 'Success')
        text = self.app.language_handler.translate(
            'startup_code_success_message',
            'Startup code verified successfully.'
        )
        accept = self.app.language_handler.translate('continue', 'CONTINUE')
        # Provide an empty string for cancel to avoid None error
        cancel = ""
        
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self._go_to_next_screen,
            cancel=cancel
        )
        
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