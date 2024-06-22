'''
KV configuration for first run.
'''

# Third-party imports.
from kivy.config import Config

# KV settings.
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '480')
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'show_cursor', '0')
Config.write()