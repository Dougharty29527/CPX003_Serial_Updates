'''
Contractor Certification Number Screen
'''

# Kivy imports
from kivy.logger import Logger
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER


class ContractorCertificationScreen(BaseOOBEScreen):
    '''
    Contractor Certification Number Screen:
    - This screen allows the user to enter the Startup Contractor Certification Number.
    - This screen comes after the CRE number entry (or after timezone verification for CS2 profile).
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "CONTRACTOR CERTIFICATION"
        self.certification_number = ""
        
        # Add translations directly
        self._add_translations_directly()
        
    def _add_translations_directly(self):
        '''
        Directly add translations to the database to ensure they are available.
        '''
        try:
            # English translations
            english_translations = {
                'enter_contractor_certification': 'ENTER STARTUP CONTRACTOR CERTIFICATION NUMBER',
                'contractor_certification_description': 'GO TO WWW.VSTHOSE.COM AND COMPLETE APPENDIX B AS YOU WALK THROUGH THIS SETUP.',
                'certification_number_hint': 'Certification Number',
                'certification_number_helper': 'Enter Startup Contractor Certification Number',
            }
            
            # Spanish translations
            spanish_translations = {
                'enter_contractor_certification': 'INGRESE EL NÚMERO DE CERTIFICACIÓN DEL CONTRATISTA DE INICIO',
                'contractor_certification_description': 'VAYA A WWW.VSTHOSE.COM Y COMPLETE EL APÉNDICE B MIENTRAS REALIZA ESTA CONFIGURACIÓN.',
                'certification_number_hint': 'Número de Certificación',
                'certification_number_helper': 'Ingrese el número de certificación del contratista de inicio',
            }
            
            # Add English translations
            for key, value in english_translations.items():
                self.app.translations_db.add_translation('EN', key, value)
            
            # Add Spanish translations
            for key, value in spanish_translations.items():
                self.app.translations_db.add_translation('ES', key, value)
                
        except Exception as e:
            Logger.error(f'OOBE: Error adding contractor certification translations: {e}')
            
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        '''
        # Add translations directly to ensure they are available
        self._add_translations_directly()
        
        # Clear the input field
        self.ids.certification_input.text = ""
        # Clear any error state
        self.ids.certification_input.error = False
        self.ids.certification_input.helper_text = ""
        
    def add_character(self, char):
        '''
        Add a character to the input field.
        '''
        current_text = self.ids.certification_input.text
        self.ids.certification_input.text = current_text + str(char)
        
    def delete_character(self):
        '''
        Remove a character from the input field.
        '''
        current_text = self.ids.certification_input.text
        
        if len(current_text) >= 1:
            current_text = current_text[:-1]
            self.ids.certification_input.text = current_text
        
    def on_certification_entered(self):
        '''
        Handle Contractor Certification number entry.
        '''
        # Get the certification number from the text field
        certification_field = self.ids.certification_input
        self.certification_number = certification_field.text.strip()
        
        if not self.certification_number:
            # Show error if certification number is empty
            certification_field.error = True
            certification_field.helper_text = "Certification number cannot be empty"
            return
            
        # Save the certification number to the database
        self.app.oobe_db.add_setting('contractor_certification_number', self.certification_number)
        
        # Mark certification number entry as complete
        self.app.oobe_db.add_setting('contractor_certification_entered', 'true')
        
        # Navigate to the Contractor Password screen
        self.next_screen('OOBEContractorPassword')
        
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
    
    def go_back(self):
        '''
        Navigate to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)