'''
============================
    File Logging Module
============================
    Instructions:
    - Initialize the Logger with a name and an optional logging level.
    - Use the `log_message` method to log a message to the log file.
    - Use the `get_log_file_path` method to get the path to the log file.
    - Use the `get_last_entries` method to get the last n entries from the log file.
'''

import logging
import os


class Logger:
    '''
    Logger
    ------
    Class to handle logging across the entire application.
    '''

    def __init__(self, name, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.filename = f'{name}.log'
        self.level = level
        self.logger.setLevel(self.level)

        if not os.path.exists(os.path.join('data', 'logs')):
            os.makedirs(os.path.join('data', 'logs'))
        self._log_directory = os.path.join('data', 'logs')

        file_handler = logging.FileHandler(os.path.join(self._log_directory, self.filename))
        file_handler.setLevel(self.level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def log_message(self, level, message):
        '''
        Parameters:
        - level (str): The logging level. If None, 'info' will be used.
        - message (str): The message to be logged.
        '''
        if level is None:
            level = 'info'
        if hasattr(logging, level):
            level_func = getattr(self.logger, level)
            level_func(message)
        else:
            self.logger.error('Logging level %s is not valid', level)

    def get_log_file_path(self):
        '''
        Returns:
        - str: The path to the log file.
        '''
        return os.path.join(self._log_directory, self.filename)

    def get_last_entries(self, num_entries):
        '''
        Parameters:
        - num_entries (int): The number of entries to retrieve.
        Returns:
        - list: The last n entries from the log file.
        '''
        try:
            with open(
                os.path.join(
                    self._log_directory,
                    self.filename
                ),
                'r',
                encoding='utf-8'
            ) as f:
                lines = f.readlines()
                last_entries = lines[-num_entries:]
                return last_entries
        except FileNotFoundError:
            self.logger.error('Log file not found.')
            return []