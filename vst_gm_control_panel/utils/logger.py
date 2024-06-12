'''
=======================================================
                File Logging Module
=======================================================
'''

import logging
import os


class Logger:
    '''
    Logger
    ------
    Class to handle logging across entire application.
    '''
    def __init__(self, name, filename='control_panel.log', level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self._log_directory = os.path.join('data', 'logs')

        if not os.path.exists(self._log_directory):
            os.makedirs(self._log_directory)

        file_handler = logging.FileHandler(os.path.join(self._log_directory, filename))
        file_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def log_message(self, level, message):
        ''' Log a message to the log file. '''
        if level is None:
            level = 'info'
        if hasattr(logging, level):
            level_func = getattr(self.logger, level)
            level_func(message)
        else:
            self.logger.error('Logging level %s is not valid', level)