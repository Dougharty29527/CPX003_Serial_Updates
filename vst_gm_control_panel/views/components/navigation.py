'''
Navigation modules.
'''

# Kivy imports.
from kivy.properties import BooleanProperty
from kivymd.uix.navigationdrawer import MDNavigationLayout, MDNavigationDrawerItem

# Local imports.
from .base_widget import BaseWidget


class SideBar(BaseWidget, MDNavigationLayout):
    ''' 
    SideBar:
    - Class to set up the expandable and collapsable side navigation bar.
    '''

    menu = None
    toggled: BooleanProperty = BooleanProperty(False)


class NavDrawerItem(BaseWidget, MDNavigationDrawerItem):
    '''
    NavDrawer:
    - Class to remove on release from button press.
    '''
    def on_release(self, *args) -> None:
        '''
        Fired when the item is released
        (i.e. the touch/click that pressed the item goes away).
        '''
        self.selected = not self.selected