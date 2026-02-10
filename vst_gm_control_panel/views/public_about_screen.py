from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from kivy.logger import Logger

class PublicAboutScreen(MDScreen):
    '''Public About Screen - Level 0 access, displays basic system information'''
    
    def __init__(self, app, **kwargs):
        Logger.info('PublicAboutScreen: Initializing')
        super().__init__(**kwargs)
        self.app = app
        # Schedule multiple updates to ensure widgets are ready
        Clock.schedule_once(self.update_info, 0)
        Clock.schedule_once(self.update_info, 0.5)

    def on_enter(self):
        '''Called when screen is entered'''
        Logger.info('PublicAboutScreen: Screen entered')
        # Schedule updates to ensure widgets are ready
        Clock.schedule_once(self.update_info, 0)
        Clock.schedule_once(self.update_info, 0.5)

    def _set_label_text(self, label_id, text):
        '''Helper method to set label text with error handling'''
        try:
            if label_id in self.ids:
                self.ids[label_id].text = text
            else:
                pass  # Label not found - this is expected for some configurations
        except Exception as e:
            Logger.error(f'PublicAboutScreen: Error setting text for {label_id}: {e}')
            try:
                if label_id in self.ids:
                    self.ids[label_id].text = 'Error loading information'
            except:
                pass

    def update_info(self, dt=None):
        '''Update all information fields with error handling'''
        
        if not self.app:
            Logger.warning('PublicAboutScreen: App instance not available')
            return

        # Get "Not Available" translation with fallback
        not_available = self.app.language_handler.translate('public_about_not_available', 'Not Available')
        if not not_available or not_available.strip() == '':
            not_available = 'Not Available'

        # Get device information
        try:
            device_name = getattr(self.app, 'device_name', not_available)
            device_text = device_name if device_name and device_name != 'N/A' else not_available
            self._set_label_text('device_name_text', str(device_text))
        except Exception as e:
            Logger.error(f'PublicAboutScreen: Error getting device name: {e}')
            self._set_label_text('device_name_text', not_available)
        
        # Get software information
        try:
            version = getattr(self.app, 'software_version', 'N/A')
            software = getattr(self.app, 'software', 'N/A')
            software_text = f'{software} v{version}' if software != 'N/A' and version != 'N/A' else not_available
            self._set_label_text('software_info_text', str(software_text))
        except Exception as e:
            Logger.error(f'PublicAboutScreen: Error getting software info: {e}')
            self._set_label_text('software_info_text', not_available)

        # Get profile information
        try:
            profile = getattr(self.app, 'profile', not_available)
            profile_text = profile if profile and profile != 'N/A' else not_available
            self._set_label_text('profile_info_text', str(profile_text))
        except Exception as e:
            Logger.error(f'PublicAboutScreen: Error getting profile info: {e}')
            self._set_label_text('profile_info_text', not_available)
        
        # Get panel serial number from gm_db
        try:
            if hasattr(self.app, 'gm_db'):
                panel_sn = self.app.gm_db.get_setting('panel_serial')
                panel_text = panel_sn if panel_sn and panel_sn != 'N/A' else not_available
            else:
                panel_text = not_available
            self._set_label_text('panel_sn_text', str(panel_text))
        except Exception as e:
            Logger.error(f'PublicAboutScreen: Error getting panel serial: {e}')
            self._set_label_text('panel_sn_text', not_available)
        
        # Get Green Machine serial number from gm_db
        try:
            if hasattr(self.app, 'gm_db'):
                gm_sn = self.app.gm_db.get_setting('gm_serial')
                gm_text = gm_sn if gm_sn and gm_sn != 'N/A' else not_available
            else:
                gm_text = not_available
            self._set_label_text('gm_sn_text', str(gm_text))
        except Exception as e:
            Logger.error(f'PublicAboutScreen: Error getting GM serial: {e}')
            self._set_label_text('gm_sn_text', not_available)

    def handle_nav(self, screen_name):
        '''Handle navigation from back button'''
        if screen_name == 'back':
            self.app.switch_screen('Main')
        else:
            self.app.switch_screen(screen_name)