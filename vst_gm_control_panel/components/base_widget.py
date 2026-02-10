'''
This module provides common operations for the widgets in the application.
'''

# Kivy imports.
from kivymd.app import MDApp


class BaseWidget:
    '''
    BaseWidget:
    - Class to handle common operations.
    '''

    app = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the BaseWidget.
        '''
        self.app = MDApp.get_running_app()