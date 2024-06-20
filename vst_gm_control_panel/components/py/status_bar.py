'''
Status bar component for handling dynamic changes.
'''

# Kivy imports.
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton


class StatusBar(MDBoxLayout):
    ''' 
    TopBar:
    - Class to set up the apps header.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the SideBar.
        '''
        self.app = MDApp.get_running_app()


# class TextButton(MDButton):
#     '''
#     TextButton:
#     - Class to remove on release from button.
#     '''
#     def on_release(self, *args) -> None:
#         '''
#         Fired when the item is released
#         (i.e. the touch/click that pressed the item goes away).
#         '''
#         self.md_bg_color = self.app.theme_cls.primaryContainerColor

#     def on_kv_post(self, base_widget):
#         '''
#         Initialize the SideBar.
#         '''
#         self.app = MDApp.get_running_app()
