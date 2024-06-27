# Standard imports.
from datetime import datetime, timezone
import subprocess
import pytz
from zoneinfo import ZoneInfo

# Kivy imports.
from kivymd.uix.screen import MDScreen
from kivy.properties import BooleanProperty, StringProperty

# Local imports.
from views.components import CustomDialog
from utils import Logger


class MainScreen(MDScreen):
    '''
    Main Screen:
    - This class sets up the Main Screen.
    '''

    _logger = Logger(__name__)

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.log = self._logger.log_message


class TestScreen(MDScreen):
    '''
    Test Screen:
    - This class sets up the Testing Screen.
    '''

    pin_entry = BooleanProperty(False)
    interval_entry = BooleanProperty(False)
    input_string = StringProperty('0')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

    def open_stat_sheet(self, stat_sheet):
        stat_sheet.drawer_type = 'standard'
        stat_sheet.set_state('toggle')

    def open_sheet(self, sheet):
        if self.pin_entry:
            self.interval_entry = False
        else:
            self.pin_entry = False
        self.input_string = '0'
        sheet.drawer_type = 'modal'
        sheet.set_state('toggle')

    def add_digit(self, digit):
        ''' Add a digit to the Test screen. '''
        self.input_string = self.ids.input_field.text
        if self.ids.input_field.text == '0':
            self.ids.input_field.text = str(digit)
        else:
            self.app.sm.get_screen('Test').ids.input_field.text = self.input_string + str(digit)

    def backspace(self):
        ''' Remove a digit from the Test screen. '''
        self.input_string = self.ids.input_field.text
        if len(self.input_string) == 1:
            self.ids.input_field.text = '0'
        else:
            self.ids.input_field.text = self.input_string[:-1]

    def submit(self):
        ''' Submit the code entered on the Test screen. '''
        code_entered = self.ids.input_field.text
        if self.pin_entry:
            self.app.set_pin_delay(int(code_entered))
            self.input_string = f'{self.app.language_handler.translate("pin_update", "Pin delay set to")} {code_entered} ms.'
        elif self.interval_entry:
            self.app.set_run_cycle_interval(int(code_entered))
            self.input_string = f'{self.app.language_handler.translate("cycle_check_interval", "Run cycle check interval set to")} {code_entered} min.'
        self.pin_entry = False
        self.interval_entry = False


class TimeEntryScreen(MDScreen):
    ''' 
    TimeEntryScreen:
    - Screen to handle manual time updates.
    '''

    time_input_string = StringProperty(':')
    _logger = Logger(__name__)

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.log = self._logger.log_message
        self.db = self.app._user_db

    def add_digit(self, digit):
        '''
        Purpose:
        - Add a digit to the input field.
        Parameters:
        - digit: The digit to add (int).
        '''
        self.time_input_string = self.ids.time_input_field.text.replace(':', '')

        if len(self.time_input_string) < 4:
            if len(self.time_input_string) == 0:
                # First digit logic for hours.
                if 3 <= digit <= 9:
                    self.time_input_string = '0' + str(digit)
                else:
                    self.time_input_string += str(digit)
            elif len(self.time_input_string) == 1:
                # Second digit logic for hours.
                self.time_input_string += str(digit)
                if int(self.time_input_string[:2]) > 24:
                    self.time_input_string = '24'
            elif len(self.time_input_string) == 2:
                # First digit logic for minutes.
                if 6 <= digit <= 9:
                    self.time_input_string += '0' + str(digit)
                else:
                    self.time_input_string += str(digit)
            else:
                # Second digit logic for minutes.
                self.time_input_string += str(digit)
                if int(self.time_input_string[2:]) > 59:
                    self.time_input_string = self.time_input_string[:2] + '59'

            self.ids.time_input_field.text = self.time_input_string[:2] + ':' + self.time_input_string[2:]

    def backspace(self):
        '''
        Purpose:
        - Remove the last digit from the input field.
        '''
        self.time_input_string = self.ids.time_input_field.text.replace(':', '')
        if self.time_input_string:
            self.time_input_string = self.time_input_string[:-1]
            self.ids.time_input_field.text = self.time_input_string[:2] + ':' + self.time_input_string[2:]

    def set_system_time(self, *args):
        '''
        Purpose:
        - Set the system time based on the time input string.
        '''
        # Current date.
        now = datetime.utcnow()
        try:
            # Stop and disable systemd-timesyncd.
            subprocess.run(['sudo', 'systemctl', 'stop', 'systemd-timesyncd'])
            subprocess.run(['sudo', 'systemctl', 'disable', 'systemd-timesyncd'])
            self.log('warning', 'Systemd-timesyncd disabled.')
        except subprocess.CalledProcessError as e:
            self.log('error', f'Failed to stop and disable systemd-timesyncd: {e}')
            return

        try:
            # Combine current date with the new time.
            new_time_str = f'{now.year}-{now.month:02d}-{now.day:02d} {self.time_input_string[:2]}:{self.time_input_string[2:]}:00'
            # Convert to datetime object.
            new_time = datetime.strptime(new_time_str, '%Y-%m-%d %H:%M:%S')
            # Format for the `date` command.
            date_command = new_time.strftime('%Y-%m-%d %H:%M:%S')

            # Set the system time using the `date` command.
            subprocess.run(['sudo', 'date', '--set', date_command])
            self.log('info', f'System time set to {date_command}')
        except Exception as e:
            self.log('error', f'Failed to set system time: {e}')
            return

        self.log('info', f'Time updated to: {self.time_input_string}')
        self.app.manual_time_set = True
        self.db.add_setting('manual_time_set', True)
        self.app.get_datetime()
        self.time_input_string = (':')

    def submit(self):
        '''
        Purpose:
        - Submit the time input and set the system time.
        '''
        self.show_dialog()

    def show_dialog(self):
        dialog = CustomDialog()
        title = self.app.language_handler.translate(
            'confirm_time_change',
            'Confirm Time Change?'
        )
        text_start = self.app.language_handler.translate(
            'confirm_time_change_message',
            'Are you sure you want to set the system time to '
        )
        text_end = self.app.language_handler.translate(
            'dialog_confirmation',
            "Click 'Accept' to confirm or 'Cancel' to return."
        )
        text = f'{text_start}{self.time_input_string[:2]}:{self.time_input_string[2:]} {text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        accept_method = self.set_system_time
        dialog.open_dialog(title, text, accept, accept_method, cancel)

    def restore_default_time(self):
        '''
        Purpose:
        - Restore the system time to the current time.
        '''
        try:
            # Stop and disable systemd-timesyncd.
            subprocess.run(['sudo', 'systemctl', 'enable', 'systemd-timesyncd'])
            subprocess.run(['sudo', 'systemctl', 'start', 'systemd-timesyncd'])
            self.log('warning', 'Systemd-timesyncd enabled.')
        except subprocess.CalledProcessError as e:
            self.log('error', f'Failed to start and enable systemd-timesyncd: {e}')
            return
        self.app.manual_time_set = False
        self.db.add_setting('manual_time_set', False)
        self.app.get_datetime()