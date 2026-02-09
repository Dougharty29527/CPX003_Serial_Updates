'''
Contractor Screen
'''

# Standard imports.
import os
from datetime import datetime

# Kivy imports.
from kivymd.uix.screen import MDScreen
from kivy.properties import BooleanProperty, StringProperty

# Local imports.
from components import CustomDialog


class ContractorScreen(MDScreen):
    '''
    ContractorScreen:
    - This class sets up the Contractor Screen.
    '''
    
    # String properties for reactive UI updates
    pressure_alarms_label_text = StringProperty('PRESSURE ALARMS:')
    pressure_alarms_status_text = StringProperty('NONE')
    vac_pump_alarms_label_text = StringProperty('VAC PUMP ALARMS:')
    vac_pump_alarms_status_text = StringProperty('NONE')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        # Initialize the text properties
        self.update_pressure_alarm_texts()
        self.update_vac_pump_alarm_texts()
        
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        - Ensure any running cycles are stopped for safety.
        - Update pressure alarm status
        '''
        # Safety measure: Always stop any cycles when entering System Config screen
        self.app.stop_any_cycle()
        # Update pressure alarm status display
        self.update_pressure_alarm_status()

    def update_pressure_alarm_status(self):
        '''Update the pressure alarm status display'''
        # Update the text properties to trigger UI updates
        self.update_pressure_alarm_texts()
        self.update_vac_pump_alarm_texts()
        
    def update_pressure_alarm_texts(self):
        '''Update the text properties for pressure alarms'''
        # Update label text
        if hasattr(self, 'app') and self.app and hasattr(self.app, 'language_handler'):
            try:
                pressure_alarms_label = self.app.language_handler.translate('pressure_alarms', 'PRESSURE ALARMS')
                self.pressure_alarms_label_text = f'{pressure_alarms_label}:'
                
                # Update status text (uppercase)
                if self.pressure_alarms_active:
                    self.pressure_alarms_status_text = self.app.language_handler.translate('gm_active', 'ACTIVE').upper()
                else:
                    self.pressure_alarms_status_text = self.app.language_handler.translate('none', 'NONE').upper()
            except (AttributeError, TypeError):
                # Use defaults if there's any issue
                self.pressure_alarms_label_text = 'PRESSURE ALARMS:'
                self.pressure_alarms_status_text = 'NONE'
        else:
            # Use defaults during initialization
            self.pressure_alarms_label_text = 'PRESSURE ALARMS:'
            self.pressure_alarms_status_text = 'NONE'
            
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
    def pressure_alarms_active(self):
        '''Check if any pressure alarms are currently active'''
        # Return False if app is not available yet (during initialization)
        if not hasattr(self, 'app') or not self.app:
            return False
    
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
            
        pressure_alarms = ['low_pressure', 'high_pressure', 'variable_pressure', 'zero_pressure']
        
        try:
            # Get current active alarms from the app
            active_alarms = self.app.get_active_alarm_names()
            
            # Check if any pressure alarms are in the active list
            for alarm in pressure_alarms:
                if alarm in active_alarms:
                    return True
        except (AttributeError, TypeError):
            # Return False if there's any issue accessing app methods
            return False
            
        return False


    @property
    def pressure_alarms_color(self):
        '''Get the color for pressure alarms status'''
        try:
            if self.pressure_alarms_active:
                # Red color for ACTIVE alarms
                return [1, 0, 0, 1]
            else:
                # Green color for NONE - convert hex to RGBA
                # app.success_color is '#2E7D32'
                return [0.18, 0.49, 0.196, 1]  # #2E7D32 converted to RGBA
        except (AttributeError, TypeError):
            # Return green color as default
            return [0.18, 0.49, 0.196, 1]

    def stop_running_cycle(self):
        '''
        Stop any running cycles and set the system to a rest state.
        '''
        self.app.io.stop_cycle()
        self.app.io.set_rest()

    def restart_application(self):
        '''
        Reboot the machine.
        '''
        self.stop_running_cycle()
        os.system('sudo reboot')

    def show_restart_dialog(self):
        '''
        Show a dialog to confirm the restart of the application.
        '''
        dialog = CustomDialog()

        title = self.app.language_handler.translate(
            'confirm_system_reboot',
            'Confirm System Reboot?'
        )
        text_start = self.app.language_handler.translate(
            'confirm_reboot_message',
            'Are you sure you want to reboot the entire system?'
        )
        text_end = self.app.language_handler.translate(
            'dialog_confirmation', 
            "Click 'Accept' to confirm or 'Cancel' to return."
        )
        text = f'{text_start}\n\n{text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.restart_application,
            cancel=cancel
        )

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
        low = self.app.language_handler.translate('low_pressure_alarm', 'Low Pressure')
        high = self.app.language_handler.translate('high_pressure_alarm', 'High Pressure')
        variable = self.app.language_handler.translate('variable_pressure_alarm', 'Variable Pressure')
        zero = self.app.language_handler.translate('zero_pressure_alarm', 'Zero Pressure')

        dialog = CustomDialog()

        title = self.app.language_handler.translate(*translations['title'])

        text_start = self.app.language_handler.translate(*translations['text_start'])
        text_end = self.app.language_handler.translate(*translations['text_end'])
        text = f'{text_start}\n{low}\n{high}\n{variable}\n{zero}\n\n{text_end}'

        accept = self.app.language_handler.translate(*translations['accept'])
        cancel = self.app.language_handler.translate(*translations['cancel'])

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.clear_pressure_alarms,
            cancel=cancel
        )

    def clear_pressure_alarms(self):
        '''
        Clear the pressure alarms.
        '''
        pressure_alarms = [
            'low_pressure',
            'high_pressure',
            'variable_pressure',
            'zero_pressure'
        ]
        for alarm in pressure_alarms:
            self.app.gm_db.add_setting(f'{alarm}_alarm', None)
            self.app.alarms_db.add_setting(f'{alarm}_start_time', None)
        
        # Turn shutdown relay back on when alarms are cleared
        self.app.io.set_shutdown_relay(True)
        
        # Reload alarm settings to apply changes immediately
        self.app.send_reload_signal()
        
        # Update pressure alarm status display
        self.update_pressure_alarm_status()
        
    def on_language_change(self):
        '''Called when language changes to update translations'''
        self.update_pressure_alarm_texts()

    def show_calibration_dialog(self):
        '''
        Show confirmation dialog for pressure sensor calibration.
        
        SERIAL-ONLY (Rev 10.7): Calibration is now performed by the ESP32, not Python.
        Sends {"type":"cmd","cmd":"cal"} to ESP32 via serial_manager.send_calibration_command().
        ESP32 collects 60 ADC samples, computes trimmed mean, saves zero point to EEPROM.
        
        The current sensor reading becomes the new 0.0 IWC reference point.
        Works correctly at any altitude — e.g., if reading -0.5 IWC before
        calibration, it will read 0.0 IWC afterward.
        
        Previously called self.app.io.pressure_sensor.calibrate which read the ADS1115
        over I2C directly — that hardware path no longer exists.
        
        Usage example:
            show_calibration_dialog()  # Opens confirmation dialog, then sends cal command
        '''
        translations = {
            'title': ('calibrate_pressure_sensor', 'Calibrate Pressure Sensor'),
            'warning': ('pressure_calibration_warning', 'WARNING:\nThe pressure sensor must be open to atmospheric air\nin order to calibrate!'),
            'confirmation': ('calibration_confirmation', 'PRESS CONFIRM WHEN READY, OR CANCEL TO EXIT.'),
            'accept': ('confirm', 'Confirm'),
            'cancel': ('cancel', 'Cancel')
        }
        dialog = CustomDialog()
        title = self.app.language_handler.translate(*translations['title'])
        warning = self.app.language_handler.translate(*translations['warning'])
        confirmation = self.app.language_handler.translate(*translations['confirmation'])
        text = f'{warning}\n\n{confirmation}'
        accept = self.app.language_handler.translate(*translations['accept']).upper()
        cancel = self.app.language_handler.translate(*translations['cancel'])

        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self._send_calibration_to_esp32,
            cancel=cancel
        )

    def _send_calibration_to_esp32(self, *args):
        '''
        Send pressure calibration command to ESP32 via serial.
        
        SERIAL-ONLY: Called when user confirms the calibration dialog.
        The ESP32 performs the actual calibration (60 samples, trimmed mean,
        EEPROM save). This replaces the old self.app.io.pressure_sensor.calibrate()
        which read the ADS1115 directly over I2C.
        
        Usage example:
            _send_calibration_to_esp32()  # Sends {"type":"cmd","cmd":"cal"} to ESP32
        '''
        from kivy.logger import Logger
        serial_mgr = getattr(self.app, 'serial_manager', None)
        if serial_mgr:
            result = serial_mgr.send_calibration_command()
            if result:
                Logger.info('PressureSensor: Calibration command sent to ESP32 — zero point will be recalculated')
            else:
                Logger.warning('PressureSensor: Failed to send calibration command to ESP32')
        else:
            Logger.error('PressureSensor: No serial manager available — cannot calibrate')
