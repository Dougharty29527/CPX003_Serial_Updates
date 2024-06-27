'''
User interaction modules.
'''

# Kivy imports.
from kivy.properties import BooleanProperty, StringProperty
from kivy.utils import hex_colormap
from kivymd.uix.bottomsheet import MDBottomSheet
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu

# Local imports.
from .base_widget import BaseWidget


class NoDragMDBottomSheet(MDBottomSheet):
    '''
    NoDragMDBottomSheet:
    - Class to disable dragging on the bottom sheet.
    '''

    def on_touch_move(self, touch):
        return False


class DropdownMenu(BaseWidget, MDDropdownMenu):
    '''
    DropdownMenu:
    - Class to set up the basic settings menu.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = None
        self.second_menu = None

    def open_menu(self, menu_button, items) -> None:
        '''
        Purpose:
        - Open the menu.
        Parameters:
        - menu_button: The button that triggered the menu (MDFloatingActionButton).
        - items: The items to add to the menu (list).
        '''
        self.dismiss_current_menu()
        menu_items = []
        for item in items:
            menu_items.append(item)
        self.menu = MDDropdownMenu(
            caller=menu_button,
            items=menu_items,
        )
        self.menu.open()

    def dismiss_current_menu(self, *args) -> None:
        '''
        Purpose:
        - Dismiss the current menu.
        '''
        if self.menu:
            self.menu.dismiss()

    def settings_menu(self, menu_button) -> None:
        '''
        Purpose:
        - Create the settings menu.
        Parameters:
        - menu_button: The button that triggered the menu (MDFloatingActionButton).
        '''
        settings_menu = [
            # {'text': f'{self.app.language_handler.translate("set_palette", "Set Palette")}', 'on_release': self.set_palette},
            {'text': f'{self.app.language_handler.translate("set_language", "Set Language")}', 'on_release': self.set_language},
            {'text': f'{self.app.language_handler.translate("time_entry", "Time Entry")}', 'on_release': self.time_selection},
            # {'text': f'{self.app.language_handler.translate("switch_theme", "Switch Theme")}', 'on_release': self.switch_theme},
            {'text': f'{self.app.language_handler.translate("dismiss", "Dismiss")}', 'on_release': lambda: self.dismiss_current_menu(self.menu)}        
        ]
        self.open_menu(menu_button, settings_menu)
    
    # def switch_theme(self) -> None:
    #     '''
    #     Purpose:
    #     - Switch the theme of the application.
    #     '''
    #     if self.app.theme_cls.theme_style == 'Light':
    #         self.app.theme_cls.theme_style = 'Dark'
    #     else:
    #         self.app.theme_cls.theme_style = 'Light'

    def switch_language(self, selected_language) -> None:
        '''
        Purpose:
        - Switch the language and go back to the settings menu.
        Parameters:
        - language: The selected language (str).
        - menu_button: The button that triggered the menu (MDFloatingActionButton).
        '''
        self.app.switch_language(selected_language)
        self.second_menu.dismiss()
        self.menu.dismiss()

    # def switch_palette(self, selected_palette) -> None:
    #     '''
    #     Purpose:
    #     - Switch the color palette of the application.
    #     Parameters:
    #     - selected_palette: The selected palette (str).
    #     '''
    #     self.app.theme_cls.primary_palette = selected_palette

    # def set_palette(self) -> None:
    #     '''
    #     Purpose:
    #     - Set the color palette of the application.
    #     '''
    #     instance_from_menu = self.get_instance_from_menu(self.app.language_handler.translate('set_palette', 'Set Palette'))
    #     available_palettes = [
    #         name_color.capitalize() for name_color in hex_colormap.keys()
    #     ]

    #     menu_items = [
    #         {
    #             'text': name_palette,
    #             'on_release': lambda x=name_palette: self.switch_palette(x)
    #         } for name_palette in available_palettes]
    #     MDDropdownMenu(
    #         caller=instance_from_menu,
    #         items=menu_items,
    #     ).open()

    def set_language(self) -> None:
        '''
        Purpose:
        - Set the language of the application.
        '''
        instance_from_menu = self.get_instance_from_menu(self.app.language_handler.translate('set_language', 'Set Language'))
        available_languages = {
            'EN': 'English',
            'ES': 'Español'
        }
        menu_items = [
            {
                'text': language_name,
                'on_release': lambda x=language_code: self.switch_language(x)
            } for language_code, language_name in available_languages.items()
        ]
        self.second_menu = MDDropdownMenu(
            caller=instance_from_menu,
            items=menu_items,
        )
        self.second_menu.open()

    def get_instance_from_menu(self, name_item) -> MDDropdownMenu:
        '''
        Purpose:
        - Get the instance from the menu.
        Parameters:
        - name_item: The name of the item (str).
        Returns:
        - The instance from the menu.
        '''
        rv = self.menu.ids.md_menu
        index = next(i for i, data in enumerate(rv.data) if data['text'] == name_item)
        return rv.view_adapter.get_view(index, rv.data[0], rv.layout_manager.view_opts[index]['viewclass'])

    def time_selection(self):
        '''
        Purpose:
        - Open the time selection screen and close the settings menu.
        '''
        self.dismiss_current_menu(self.menu)
        self.app.switch_screen('TimeEntry')


class TopBar(BaseWidget, MDBoxLayout):
    ''' 
    TopBar:
    - Class to set up the apps header.
    '''

    pass


class Diagnostics(NoDragMDBottomSheet):
    '''
    Diagnostics:
    - Class to display the diagnostics menu.
    '''
    pass