'''
Side Bar Python Component for handling dynamic changes.
'''

# Standard imports.
from typing import List, Optional

# Kivy imports.
from kivy.app import App
from kivy.properties import BooleanProperty
from kivymd.uix.button import MDIconButton
from kivymd.uix.navigationdrawer import (
    MDNavigationLayout,
    MDNavigationDrawerItem,
    MDNavigationDrawerItemLeadingIcon,
    MDNavigationDrawerItemText
)


class SideBar(MDNavigationLayout):
    ''' 
    SideBar:
    - Class to set up the expandable and collapsable side navigation bar.
    '''

    menu = None
    toggled: BooleanProperty = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the SideBar.
        '''
        self.sidebar_append()

    def switch_screen(self, screen_name: Optional[str] = None) -> None:
        '''
        Purpose:
        - Interacts with parent app to switch screens.
        Parameters:
        - instance: screen name (str).
        '''
        app = App.get_running_app()
        if screen_name:
            print(screen_name)
            # app.sm.current = screen_name
        else:
            # app.sm.current = 'main_screen'
            print('main_screen')

    def sidebar_container_config(self) -> dict:
        '''
        Purpose:
        - Configuration for Closed Nav Buttons.
        Returns:
        - dict: Configuration for Closed Nav Buttons.
        '''
        return {
                'main_screen': {
                    'name': 'Main',
                    'icon': 'home'
                },
                'maintenance_screen': {
                    'name': 'Maintenance',
                    'icon': 'wrench'
                },
                'faults_screen': {
                    'name': 'Faults',
                    'icon': 'alert'
                }
            }

    def sidebar_append(self):
        '''
        Purpose:
        - Iterates over the configuration dictionary and creates buttons for the sidebar.
        '''
        for key, value in self.sidebar_container_config().items():
            collapsed_items = MDIconButton(
                icon=value['icon'],
                on_release=lambda _, key=key: self.switch_screen(key)
            )
            expanded_items = MDNavigationDrawerItem(
                MDNavigationDrawerItemLeadingIcon(icon=value['icon']),
                MDNavigationDrawerItemText(text=value['name']),
                
            )
            self.ids.closed_nav.add_widget(collapsed_items)
            self.ids.open_nav_drawer.add_widget(expanded_items)
