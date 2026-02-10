'''
Module for handling language translations.
'''

# Standard imports.
import locale
from datetime import datetime
from zoneinfo import ZoneInfo

# Kivy imports.
from kivymd.app import MDApp


class LanguageHandler:
    '''
    Class for handling language translations.
    '''
    
    def __init__(self):
        self.app = MDApp.get_running_app()

    def load_user_language(self):
        '''
        Load the user's language from the database.
        '''
        language = self.app.user_db.get_setting('language')
        if language is None:
            language = 'EN'
            self.save_user_language(language)
        self.app.language = language

    def save_user_language(self, language):
        '''
        Save the user's language to the database.
        '''
        self.app.user_db.add_setting('language', language)

    def translate(self, key, default=None) -> str:
        '''
        Translate a key to the current language.
        '''
        language = self.app.language
        translation = self.app.translations_db.translate(language, key)
        if translation is None:
            if default:
                translation = default
        return translation

    def switch_language(self, selected_language):
        '''
        Switch the language and go back to the settings menu.
        '''
        self.app.language = selected_language
        self.save_user_language(selected_language)
        self.app.get_datetime()
        self.check_all_screens()
        self.app.cycle_alarms()
        faults_screen = self.app.get_screen('Faults')
        if faults_screen:
            faults_screen.update_alarm_screen()
        debug_string = self.translate('debug', 'debug')
        self.app.debug_mode_string = debug_string.upper()
        self.app.check_alarms()

    def walk_app_widget_tree(self, widget):
        '''
        Walk the widget tree and perform translations.
        '''
        # Check if widget has 'ids' attribute and it's not empty.
        if hasattr(widget, 'ids') and widget.ids:
            for key, val in widget.ids.items():
                # Translate and update text if applicable
                if hasattr(val, 'text'):
                    translated_text = self.translate(key)
                    if translated_text is not None:
                        val.text = translated_text.upper()
                    if key == 'pin_delay_0':
                        pin_delay = self.translate('pin_delay', 'pin_delay')
                        if pin_delay is not None:
                            val.text = pin_delay.upper()
                    if key == 'run_cycle_check_interval_0':
                        interval_check = self.translate('run_cycle_check_interval', 'run_cycle_check_interval')
                        if interval_check is not None:
                            val.text = interval_check.upper()
                    if key == 'gm_status_0':
                        gm = self.translate('gm_status', 'GREEN MACHINE STATUS')
                        if gm is not None:
                            val.text = gm.upper()
                self.update_screen_title(key, val)
        # Recursively walk through children widgets
        for child in widget.children:
            self.walk_app_widget_tree(child)

    def update_screen_title(self, key, val):
        for screen, screen_name in {
            'main_screen': 'main',
            'test_screen': 'test',
            'time_entry_screen': 'time_entry'
        }.items():
            if key == screen:
                title = self.translate(screen_name, screen_name)
                val.screen_title = title.upper()

    def check_all_screens(self, *args):
        '''
        Iterate through all screens in ScreenManager and apply walk_widget_tree
        '''
        for screen in self.app.sm.screens:
            self.walk_app_widget_tree(screen)
            # Call custom language change method if it exists
            if hasattr(screen, 'on_language_change'):
                try:
                    screen.on_language_change()
                except Exception as e:
                    # Log error but continue with other screens
                    print(f"Error calling on_language_change for {screen.__class__.__name__}: {e}")