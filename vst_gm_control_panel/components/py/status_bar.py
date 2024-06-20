'''
Status bar component for handling dynamic changes.
'''

# Kivy imports.
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton


class StatusBar(MDBoxLayout):
    ''' 
    TopBar:
    - Class to set up the apps header.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the SideBar.
        '''
        self.app = MDApp.get_running_app()
