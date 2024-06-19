'''
Side Bar Python Component for handling dynamic changes.
'''

# Standard imports.
from typing import List, Optional, Union

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
                'main_screen': {'name': 'main', 'icon': 'home'},
                'maintenance_screen': {'name': 'maintenance', 'icon': 'wrench'},
                'faults_screen': {'name': 'faults', 'icon': 'alert'}
            }

    def calculate_spacing(self, total_icon_height: float, item_count: int) -> float:
        '''
        Purpose:
        - Calculate the spacing between the icons in the navigation bar.
        Parameters:
        - total_icon_height: The total height of all the icons (float).
        - item_count: The number of items in the navigation bar (int).
        Returns:
        - float: The calculated spacing.
        '''
        screen_height = self.app.height
        static_expanded_icon_height = (
            self.ids.close_nav_button.height + self.ids.settings_button.height
        )
        remaining_space = screen_height - total_icon_height
        return remaining_space / item_count / 2

    def create_button(
        self, screen_name: str,
        icon: str, name: str,
        expanded: bool =False
    ) -> Union[MDNavigationDrawerItem, MDIconButton]:
        '''
        Purpose:
        - Create a button for the navigation bar.
        Parameters:
        - screen_name: The name of the screen that the button will switch to (str).
        - icon: The icon for the button (str).
        - name: The name of the button (str).
        - expanded: Whether the button is expanded or not (bool).
        Returns:
        - MDNavigationDrawerItem or MDIconButton: The created button.
        '''
        if expanded:
            return MDNavigationDrawerItem(
                MDNavigationDrawerItemLeadingIcon(
                    icon=icon
                ),
                MDNavigationDrawerItemText(
                    text=self.app.translate(name),
                    font_style='Title',
                    role='medium'
                ),
                on_press=lambda _: self.switch_screen(screen_name)
            )
        else:
            return MDIconButton(icon=icon, on_release=lambda _: self.switch_screen(screen_name))
        

    def sidebar_append(self) -> None:
        '''
        Purpose:
        - Append buttons to the navigation bar.
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

        new_expanded_spacing = self.calculate_spacing(expanded_icons_height, expanded_item_total)
        self.ids.open_nav_drawer.spacing = new_expanded_spacing

