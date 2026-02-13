'''
Maintenance Screen
'''

# Standard imports
from datetime import datetime

# Kivy imports.
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty

# Local imports.
from components import CustomDialog


class MaintenanceScreen(MDScreen):
    '''
    Maintenance Screen:
    - This class sets up the Main Screen.
    '''
    
    # String properties for reactive UI updates
    vac_pump_alarms_label_text = StringProperty('VAC PUMP ALARMS:')
    vac_pump_alarms_status_text = StringProperty('NONE')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        # Initialize the text properties
        self.update_vac_pump_alarm_texts()
        
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        - Ensure any running cycles are stopped for safety.
        '''
        # Safety measure: Always stop any cycles when entering maintenance screen
        self.app.stop_any_cycle()
        # Update vac pump alarm status display
        self.update_vac_pump_alarm_status()

    def clear_vac_pump_alarm(self):
        '''
        Clear the vacuum pump alarm.
        '''
        self.app.alarms_db.add_setting('vac_pump_start_time', None)
        self.app.alarms_db.add_setting('vac_pump_failure_count', None)
        self.app.gm_db.add_setting('vac_pump_alarm', None)
        
        # Turn shutdown relay back on when vac pump alarm is cleared
        self.app.io.set_shutdown_relay(True)
        
        # Action completed
        pass
        
        # Reload alarm settings to apply changes immediately
        self.app.send_reload_signal()
        
        # Update vac pump alarm status display
        self.update_vac_pump_alarm_status()

    def show_clear_alarm_dialog(self):
        '''
        Show confirmation pop up.
        '''
        translations = {
            'title': ('confirm_alarm_clear', 'Clear Alarm?'),
            'text_start': ('confirm_alarm_clear_message', 'Are you sure you want to reset the alarm condition and duration?'),
            'text_end': ('dialog_confirmation', "Click 'Accept' to confirm or 'Cancel' to return."),
            'accept': ('accept', 'Accept'),
            'cancel': ('cancel', 'Cancel')
        }
        vac_pump_alarm = self.app.language_handler.translate('vac_pump', 'Vac Pump')
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
            accept_method=self.clear_vac_pump_alarm,
            cancel=cancel
        )
        
    def update_vac_pump_alarm_status(self):
        '''Update the vac pump alarm status display'''
        # Update the text properties to trigger UI updates
        self.update_vac_pump_alarm_texts()
        
    def update_vac_pump_alarm_texts(self):
        '''Update the text properties for vac pump alarms'''
        # Update label text
        if hasattr(self, 'app') and self.app and hasattr(self.app, 'language_handler'):
            try:
                vac_pump_alarms_label = self.app.language_handler.translate('vac_pump_alarms', 'VAC PUMP ALARMS')
                self.vac_pump_alarms_label_text = f'{vac_pump_alarms_label}:'
                
                # Update status text (uppercase)
                if self.vac_pump_alarms_active:
                    self.vac_pump_alarms_status_text = self.app.language_handler.translate('gm_active', 'ACTIVE').upper()
                else:
                    self.vac_pump_alarms_status_text = self.app.language_handler.translate('none', 'NONE').upper()
            except (AttributeError, TypeError):
                # Use defaults if there's any issue
                self.vac_pump_alarms_label_text = 'VAC PUMP ALARMS:'
                self.vac_pump_alarms_status_text = 'NONE'
        else:
            # Use defaults during initialization
            self.vac_pump_alarms_label_text = 'VAC PUMP ALARMS:'
            self.vac_pump_alarms_status_text = 'NONE'

    @property
    def vac_pump_alarms_active(self):
        '''Check if any vac pump alarms are currently active'''
        # Return False if app is not available yet (during initialization)
        if not hasattr(self, 'app') or not self.app:
            return False
            
        vac_pump_alarms = ['vac_pump_alarm']  # Add other vac pump alarm types as needed
        
        try:
            # Get current active alarms from the app
            active_alarms = self.app.get_active_alarm_names()
            
            # Check if any vac pump alarms are in the active list
            for alarm in vac_pump_alarms:
                if alarm in active_alarms:
                    return True
        except (AttributeError, TypeError):
            # Return False if there's any issue accessing app methods
            return False
            
        return False

    @property
    def vac_pump_alarms_color(self):
        '''Get the color for vac pump alarms status'''
        try:
            if self.vac_pump_alarms_active:
                # Red color for ACTIVE alarms
                return [1, 0, 0, 1]
            else:
                # Green color for NONE - convert hex to RGBA
                # app.success_color is '#2E7D32'
                return [0.18, 0.49, 0.196, 1]  # #2E7D32 converted to RGBA
        except (AttributeError, TypeError):
            # Return green color as default
            return [0.18, 0.49, 0.196, 1]
            
    def on_language_change(self):
        '''Called when language changes to update translations'''
        self.update_vac_pump_alarm_texts()
