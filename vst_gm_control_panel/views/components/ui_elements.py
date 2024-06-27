'''
UI elements for the application.
'''

# Kivy imports.
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogContentContainer,
    MDDialogHeadlineText,
    MDDialogSupportingText,
    MDDialogButtonContainer
)
from kivymd.uix.divider import MDDivider
from kivy.uix.widget import Widget

# Local imports.
from .base_widget import BaseWidget

class CustomDialog(MDDialog):
    ''' 
    CustomDialog:
    - Class to manage custom dialogs.
    '''
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the BaseWidget.
        '''
        self.app = MDApp.get_running_app()
        self.theme_bg_color = 'Custom'
        self.md_bg_color = self.app.theme_cls.surfaceColor

    def on_leave(self, *args):
        '''
        Purpose:
        - Remove on_leave animations.
        '''
        pass

    def on_press(self, *args):
        '''
        Purpose:
        - Remove on_press animations.
        '''
        pass

    def on_release(self, *args):
        '''
        Purpose:
        - Remove on_release animations.
        '''
        pass

    def open_dialog(
        self,
        title,
        text=None,
        accept=None,
        accept_method=None,
        cancel=None
        ):
        '''
        Purpose:
        - Open a dialog box.
        Parameters:
        - title: str
        - text: str (optional)
        - accept: str (optional)
        '''

        title = MDDialogHeadlineText(text=title)
        text = MDDialogSupportingText(text=text)
        accept = MDButton(
            MDButtonText(text=accept),
            style='text',
            radius='5dp',
            on_release=lambda x: (accept_method(), self.dismiss())
        )
        cancel = MDButton(
            MDButtonText(text=cancel),
            style='text',
            radius='5dp',
            on_release=lambda x: self.dismiss()
        )
        button_container = MDDialogButtonContainer(
            Widget(),
            accept,
            cancel,
            spacing='8dp'
        )

        for x in [title, text, MDDialogContentContainer(), button_container]:
            self.add_widget(x)
        self.open()

        

class StatusBar(BaseWidget, MDBoxLayout):
    ''' 
    StatusBar:
    - Class to manage status updates.
    '''

    pass

class TopBar(BaseWidget, MDBoxLayout):
    ''' 
    TopBar:
    - Class to set up the apps header.
    '''

    pass

