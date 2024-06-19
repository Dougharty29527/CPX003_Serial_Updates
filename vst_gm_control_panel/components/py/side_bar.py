'''
Side Bar Python Component for handling dynamic changes.
'''

# Standard imports.
from typing import List, Optional

# Kivy imports.
from kivy.app import App
from kivy.metrics import dp
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
    app = None
    toggled: BooleanProperty = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the SideBar.
        '''
        self.app = App.get_running_app()
        self.sidebar_append()

    def switch_screen(self, screen_name: Optional[str] = None) -> None:
        '''
        Purpose:
        - Interacts with parent app to switch screens.
        Parameters:
        - instance: screen name (str).
        '''
        if screen_name:
            print(screen_name)
            # self.app.sm.current = screen_name
        else:
            # self.app.sm.current = 'main_screen'
            print('main_screen')

    def sidebar_container_config(self) -> dict:
        '''
        Purpose:
        - Configuration for Closed Nav Buttons.
        Returns:
        - dict: Configuration for Closed Nav Buttons.
        '''
        return {
                'main_screen': {'name': 'Main', 'icon': 'home'},
                'maintenance_screen': {'name': 'Maintenance', 'icon': 'wrench'},
                'faults_screen': {'name': 'Faults', 'icon': 'alert'},
                'test_screen': {'name': 'Test', 'icon': 'test-tube'}
            }

    def calculate_spacing(self, total_icon_height, item_count) -> float:
        screen_height = self.app.height
        static_expanded_icon_height = (
            self.ids.close_nav_button.height + self.ids.settings_button.height
        )
        remaining_space = screen_height - total_icon_height
        return remaining_space / item_count / 2

    def create_button(self, screen_name, icon, name, expanded=False):
        if expanded:
            return MDNavigationDrawerItem(
                MDNavigationDrawerItemLeadingIcon(
                    icon=icon
                ),
                MDNavigationDrawerItemText(
                    text=name,
                    font_style='Title',
                    role='medium'
                ),
                on_press=lambda _: self.switch_screen(screen_name)
            )
        else:
            return MDIconButton(icon=icon, on_release=lambda _: self.switch_screen(screen_name))
        

    def sidebar_append(self):
        '''
        Purpose:
        - Iterates over the configuration dictionary and creates buttons for the sidebar.
        '''
        expanded_item_total = 0
        new_icon_height = 0
        expanded_icons_height = 0

        for key, value in self.sidebar_container_config().items():
            collapsed_items = self.create_button(key, value['icon'], value['name'])
            expanded_items = self.create_button(key, value['icon'], value['name'], expanded=True)
            expanded_item_total += 1
            expanded_icons_height += expanded_items.height
            self.ids.closed_nav.add_widget(collapsed_items)
            self.ids.open_nav_drawer.add_widget(expanded_items)

        new_expanded_padding = self.calculate_spacing(expanded_icons_height, expanded_item_total)
        self.ids.open_nav_drawer.spacing = new_expanded_padding
