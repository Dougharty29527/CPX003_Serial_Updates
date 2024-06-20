from kivymd.uix.screen import MDScreen

''' 
Test Screen.

This module defines the MainScreen class, which represents the main screen of the application.
'''



class TestScreen(MDScreen):
    '''
    Test Screen
    -----------
    This class sets up the Testing Screen.
    '''

    def __init__(self, app, **kwargs):
        '''
        Parameters:
            app (App): The main application instance.
            name (str, optional): The name of the screen. Defaults to None.
        '''
        super().__init__(**kwargs)
        self.app = app
