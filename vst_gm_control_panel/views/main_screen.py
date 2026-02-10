'''
Main Screen
'''

# Kivy imports.
from kivymd.uix.screen import MDScreen


class MainScreen(MDScreen):
    '''
    Main Screen:
    - This class sets up the Main Screen.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app