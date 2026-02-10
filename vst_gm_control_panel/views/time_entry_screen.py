'''
Time Entry Screen
'''

# Standard imports.
from datetime import datetime, timedelta
import subprocess
from zoneinfo import ZoneInfo

# Kivy imports.
from kivy.logger import Logger
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty

# Local imports.
from components import CustomDialog


class TimeEntryScreen(MDScreen):
    ''' 
    TimeEntryScreen:
    - Screen to handle manual time updates.
    '''

    time_input_string = StringProperty(':')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

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
        # Get the current system time before making any changes.
        current_time = datetime.now()
        # Current date.
        now = datetime.utcnow()
        try:
            # Stop and disable systemd-timesyncd.
            subprocess.run(['sudo', 'systemctl', 'stop', 'systemd-timesyncd'])
            subprocess.run(['sudo', 'systemctl', 'disable', 'systemd-timesyncd'])
            Logger.info('System-timesyncd disabled')
            Logger.warning('Systemd-timesyncd disabled')
        except subprocess.CalledProcessError as e:
            # self.log('error', f'Failed to stop and disable systemd-timesyncd: {e}')
            Logger.error(f'Failed to stop and disable systemd-timesyncd: {e}')
            return

        try:
            # Combine current date with the new time.
            new_time_str = f'{now.year}-{now.month:02d}-{now.day:02d} {self.time_input_string[:2]}:{self.time_input_string[2:]}:00'
            # Convert to datetime object.
            new_time = datetime.strptime(new_time_str, '%Y-%m-%d %H:%M:%S')

            # Format for the `date` command.
            date_command = new_time.strftime('%Y-%m-%d %H:%M:%S')
            # Calculate the time difference
            time_difference = new_time - current_time

            # Set the system time using the `date` command.
            subprocess.run(['sudo', 'date', '--set', date_command])
            Logger.info(f'System time set to {date_command}')
        except Exception as e:
            Logger.error(f'Failed to set system time: {e}')
            return
        # Adjust alarm start times in the database
        self.app.alarm_manager.update_alarm_start_times(time_difference)
        self.app.profile_handler.load_alarms()
        # self.log('info', f'Time updated to: {self.time_input_string}')
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
        text = f'{text_start}{self.time_input_string[:2]}:{self.time_input_string[2:]}?\n\n{text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        accept_method = self.set_system_time
        dialog.open_dialog(title, text, accept, accept_method, cancel)

    def restore_default_time(self):
        '''
        Purpose:
        - Restore the system time to the current time.
        '''
        # Get the current system time before making any changes.
        current_time = datetime.now()

        try:
            # Enable and start systemd-timesyncd.
            subprocess.run(['sudo', 'systemctl', 'enable', 'systemd-timesyncd'])
            subprocess.run(['sudo', 'systemctl', 'start', 'systemd-timesyncd'])
            Logger.warning('Systemd-timesyncd enabled')
            new_time = datetime.now()
            # Calculate the time difference
            time_difference = new_time - current_time

        except subprocess.CalledProcessError as e:
            Logger.error(f'Failed to start and enable systemd-timesyncd: {e}')
            return
        # Adjust alarm start times in the database
        self.app.alarm_manager.update_alarm_start_times(time_difference)
        self.app.profile_handler.load_alarms()
        self.app.manual_time_set = False
        self.app.get_datetime()
        self.app.user_db.add_setting('manual_time_set', False)