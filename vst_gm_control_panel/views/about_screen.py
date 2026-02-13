from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from kivy.logger import Logger
import subprocess

class AboutScreen(MDScreen):
    '''VST Admin level screen displaying information about the application and device'''
    def __init__(self, app, **kwargs):
        Logger.info('AboutScreen: Initializing')
        super().__init__(**kwargs)
        self.app = app
        # Schedule multiple updates to ensure widgets are ready
        Clock.schedule_once(self.update_info, 0)   # Immediate
        Clock.schedule_once(self.update_info, 0.5)  # After half second
        Clock.schedule_once(self.update_info, 1)   # After one second

    def on_enter(self):
        '''Called when screen is entered'''
        Logger.info('AboutScreen: Screen entered')
        # Schedule multiple updates to ensure widgets are ready
        Clock.schedule_once(self.update_info, 0)   # Immediate
        Clock.schedule_once(self.update_info, 0.5)  # After half second
        Clock.schedule_once(self.update_info, 1)   # After one second

    def _get_serial_status(self):
        '''Get serial connection status'''
        if not hasattr(self.app, 'serial_manager'):
            Logger.warning('AboutScreen: No serial_manager available')
            return None
        try:
            return self.app.serial_manager.online
        except Exception as e:
            Logger.error(f'AboutScreen: Error getting serial status: {e}')
            return None

    def _get_pi_serial_number(self):
        '''Get the full Raspberry Pi serial number from /proc/cpuinfo'''
        try:
            cmd = "cat /proc/cpuinfo | grep Serial | awk '{print $3}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except Exception as e:
            Logger.error(f'AboutScreen: Error getting Pi serial number: {e}')
            return None

    def _set_supporting_text(self, widget_id, text):
        '''Helper method to set supporting text'''
        try:
            # Get the supporting text widget directly using its ID
            text_widget_id = f'{widget_id}_text'
            if text_widget_id in self.ids:
                self.ids[text_widget_id].text = text
            else:
                pass  # Widget not found - this is expected for some configurations
        except Exception as e:
            Logger.error(f'AboutScreen: Error setting text for {widget_id}: {e}')
            # Set a default error message
            try:
                text_widget_id = f'{widget_id}_text'
                if text_widget_id in self.ids:
                    self.ids[text_widget_id].text = 'Error loading information'
            except:
                pass

    def update_info(self, dt=None):
        '''Update all information fields with error handling
        
        Args:
            dt: Delta time from Kivy Clock (not used but required)
        '''
        
        if not self.app:
            Logger.warning('AboutScreen: App instance not available')
            return

        # Get software information
        try:
            version = getattr(self.app, 'software_version', 'N/A')
            software = getattr(self.app, 'software', 'N/A')
            self._set_supporting_text('software_info', f'{software} v{version}')
        except Exception as e:
            Logger.error(f'AboutScreen: Error getting software info: {e}')
            self._set_supporting_text('software_info', 'Error getting software info')

        # Get serial connection status
        try:
            not_available = self.app.language_handler.translate('admin_about_not_available', 'Not Available') or 'Not Available'
            serial_online = self._get_serial_status()
            
            if hasattr(self.app, 'serial_manager'):
                status = (self.app.language_handler.translate('admin_about_online', 'Connected')
                         if serial_online
                         else self.app.language_handler.translate('admin_about_offline', 'Disconnected'))
            else:
                status = not_available
            
            self._set_supporting_text('network_status', status)
        except Exception as e:
            Logger.error(f'AboutScreen: Error getting network status: {e}')
            self._set_supporting_text('network_status', 'Error getting network status')

        # Get device information from database
        try:
            not_available = self.app.language_handler.translate('admin_about_not_available', 'Not Available') or 'Not Available'
            
            # Device Name
            device_name = getattr(self.app, 'device_name', not_available)
            self._set_supporting_text('device_name', str(device_name))

            # Raspberry Pi Serial Number
            try:
                pi_serial = self._get_pi_serial_number()
                pi_serial_upper = str(pi_serial).upper() if pi_serial else not_available
                self._set_supporting_text('pi_serial', pi_serial_upper)
            except Exception as e:
                Logger.error(f'AboutScreen: Error getting Pi serial: {e}')
                self._set_supporting_text('pi_serial', not_available)

            # Panel Serial Number - from gm_db
            if hasattr(self.app, 'gm_db'):
                panel_sn = self.app.gm_db.get_setting('panel_serial')
                self._set_supporting_text('panel_sn', str(panel_sn) if panel_sn else not_available)
            else:
                self._set_supporting_text('panel_sn', not_available)

            # Green Machine Serial Number - from gm_db
            if hasattr(self.app, 'gm_db'):
                gm_sn = self.app.gm_db.get_setting('gm_serial')
                self._set_supporting_text('gm_sn', str(gm_sn) if gm_sn else not_available)
            else:
                self._set_supporting_text('gm_sn', not_available)

            # CRE Number - from gm_db (consolidated storage)
            if hasattr(self.app, 'gm_db'):
                cre_number = self.app.gm_db.get_setting('cre_number')
                self._set_supporting_text('cre', str(cre_number) if cre_number else not_available)
            else:
                self._set_supporting_text('cre', not_available)
                
        except Exception as e:
            Logger.error(f'AboutScreen: Error getting device info: {e}')
            for widget in ['device_name', 'pi_serial', 'panel_sn', 'gm_sn', 'cre']:
                self._set_supporting_text(widget, not_available)

        # Get profile and language info separately
        try:
            profile = getattr(self.app, 'profile', not_available)
            self._set_supporting_text('profile', str(profile))
            
            language = getattr(self.app, 'language', 'EN')
            self._set_supporting_text('language', str(language))
        except Exception as e:
            Logger.error(f'AboutScreen: Error getting profile/language info: {e}')
            self._set_supporting_text('profile', not_available)
            self._set_supporting_text('language', not_available)

        # Get cycle counts
        try:
            run_cycles = getattr(self.app, 'current_run_cycle_count', not_available)
            self._set_supporting_text('run_cycles', str(run_cycles))
            
            # Manual cycle count - from gm_db
            if hasattr(self.app, 'gm_db'):
                manual_cycles = self.app.gm_db.get_setting('manual_cycle_count')
                self._set_supporting_text('manual_cycles', str(manual_cycles) if manual_cycles else not_available)
            else:
                self._set_supporting_text('manual_cycles', not_available)
        except Exception as e:
            Logger.error(f'AboutScreen: Error getting cycle counts: {e}')
            self._set_supporting_text('run_cycles', not_available)
            self._set_supporting_text('manual_cycles', not_available)

    def on_leave(self):
        '''Called when screen is left'''
        pass

    def on_pre_leave(self):
        '''Called before screen is left'''
        pass

    def handle_nav(self, screen_name):
        '''Handle navigation from TopBar'''
        self.app.switch_screen(screen_name)