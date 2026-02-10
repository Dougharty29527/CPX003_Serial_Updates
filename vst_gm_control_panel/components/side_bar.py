'''
Sidebar component module.
'''

# Kivy imports.
from kivy.properties import BooleanProperty
from kivymd.uix.navigationdrawer import MDNavigationLayout

# Local imports.
from .base_widget import BaseWidget


class SideBar(BaseWidget, MDNavigationLayout):
    '''
    This class sets up the expandable and collapsible sidebar.
    '''
    menu = None
    toggled: BooleanProperty = BooleanProperty(False)