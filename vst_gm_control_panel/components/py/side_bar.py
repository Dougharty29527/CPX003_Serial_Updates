''' side_bar.py '''

from kivy.properties import BooleanProperty
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
        print(self.ids.closed_nav.test)