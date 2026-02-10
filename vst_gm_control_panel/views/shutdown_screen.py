'''
Shutdown Screen
'''

# Kivy imports.
from kivymd.uix.screen import MDScreen


class ShutdownScreen(MDScreen):
    '''
    This class sets up the Shutdown Screen.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app