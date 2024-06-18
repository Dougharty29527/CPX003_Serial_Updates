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
    toggled: BooleanProperty = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the SideBar.
        '''
        self.closed_nav_append()

    def closed_nav_config(self) -> dict:
        '''
        Func:
        - Configuration for Closed Nav Buttons.
        Returns:
        - dict: Configuration for Closed Nav Buttons.
        '''
        return {
                'main_screen': 'home',
                'maintenance_screen': 'wrench',
                'faults_screen': 'alert-circle'
            }

    def closed_nav_append(self):
        '''
        Func:
        - Iterates over the configuration dictionary and creates buttons for each entry.
        '''
        for key, value in self.closed_nav_config().items():
            button = MDIconButton(
                icon=value,
                on_release=lambda _, key=key: self.switch_screen(key)
            )
            self.ids.closed_nav.add_widget(button)

    def switch_screen(self, screen_name: Optional[str] = None) -> None:
        '''
        Func:
        - Interacts with parent app to switch screens.
        Params:
        - instance: screen name (str).
        '''
        app = App.get_running_app()
        if screen_name:
            print(screen_name)
            # app.sm.current = screen_name
        else:
            # app.sm.current = 'main_screen'
            print('main_screen')