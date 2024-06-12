''' Main Screen. '''

from kivy.lang import Builder
from kivymd.uix.screen import MDScreen


class MainScreen(MDScreen):
    '''
    Class for the Main Screen.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        ''' Return the KV string. '''
        return Builder.load_string(KV)

    
KV = '''
<MainScreen>
    md_bg_color: "yellow"
'''