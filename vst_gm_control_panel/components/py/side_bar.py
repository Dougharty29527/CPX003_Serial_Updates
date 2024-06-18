'''
Side Bar Python Component for handling dynamic changes.
'''

# Standard imports.
from typing import List, Optional

# Kivy imports.
from kivy.app import App
from kivy.properties import BooleanProperty
from kivymd.uix.button import MDIconButton
from kivymd.uix.navigationdrawer import MDNavigationLayout


class SideBar(MDNavigationLayout):
    ''' 
    Side Nav Bar
    ------------
    This class sets up the expandable and collapsable side navigation bar.
    '''

    menu = None
    toggled = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the SideBar.
        '''
        self.closed_nav_append()

    def closed_nav_config(self):
        '''
        Closed Nav Buttons.
        '''
        return {
            'main': {
                'icon': 'home'
            },
            'maintenance': {
                'icon': 'wrench'
            },
            'faults': {
                'icon': 'alert'
            }
        }

    def closed_nav_append(self):
        '''
        Append Closed Nav Buttons.
        '''
        for k, v in self.closed_nav_config().items():
            button = MDIconButton(icon=v['icon'])
            self.ids.closed_nav.add_widget(button)