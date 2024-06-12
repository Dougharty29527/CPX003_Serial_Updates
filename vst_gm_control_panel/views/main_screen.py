''' Main Screen. '''

from kivymd.uix.screen import MDScreen

KV = '''
<MainScreen>
    md_bg_color: self.theme_cls.onPrimaryColor
'''


class MainScreen(MDScreen):
    '''
    Class for the Main Screen.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Main'

    def build(self):
        ''' Load the .kv file. '''
        Builder.load_string(KV)
