'''
Settings Menu Component.
'''

# Kivy imports.
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivy.utils import hex_colormap


class SettingsMenu(MDDropdownMenu):
    '''
    SettingsMenu:
    - Class to set up the settings menu.
    '''

    app = None
    settings: MDDropdownMenu = None
    languages: MDDropdownMenu = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        '''
        Initialize the settings menu.
        '''
        self.app = MDApp.get_running_app()

    def settings_menu(self, menu_button) -> None:
        '''
        Purpose:
        - Open the settings menu.
        Parameters:
        - menu_button: The button that triggered the menu (MDFloatingActionButton).
        '''
        menu_items = [
            {'text': 'Set Palette', 'on_release': self.set_palette},
            {'text': 'Switch Theme', 'on_release': self.switch_theme},
            {'text': 'Switch Language', 'on_release': lambda: self.select_language(menu_button)},
            {'text': 'Close', 'on_release': lambda: self.dismiss_current_menu(self.settings)},
        ]

        if self.settings:
            self.settings.dismiss()
        self.settings = MDDropdownMenu(
            caller=menu_button,
            items=menu_items,
        )
        self.settings.open()

    def select_language(self, menu_button) -> None:
        '''
        Purpose:
        - Open the language selection menu.
        Parameters:
        - menu_button: The button that triggered the menu (MDFloatingActionButton).
        '''
        if self.settings:
            self.settings.dismiss()  # Close the current menu if it exists
        menu_items = [
            {'text': 'Back', 'on_release': lambda: self.go_back_to_settings_menu(menu_button)},
            {'text': 'English', 'on_release': lambda: self.switch_language_and_go_back('EN', menu_button)},
            {'text': 'Español', 'on_release': lambda: self.switch_language_and_go_back('ES', menu_button)},
        ]
        if self.languages:
            self.languages.dismiss()
        self.languages = MDDropdownMenu(
            caller=menu_button,
            items=menu_items,
        )
        self.languages.open()

    def switch_language_and_go_back(self, language, menu_button) -> None:
        '''
        Purpose:
        - Switch the language and go back to the settings menu.
        Parameters:
        - language: The selected language (str).
        - menu_button: The button that triggered the menu (MDFloatingActionButton).
        '''
        self.on_lang(language)
        if self.languages:
            self.languages.dismiss()
        self.settings_menu(menu_button)

    def on_lang(self, language) -> None:
        '''
        Purpose:
        - Switch the language.
        Parameters:
        - language: The selected language (str).
        '''
        for widget in self.walk():
            if hasattr(widget, 'text'):
                widget.text = self.translate(widget.text)
        if language:
            self.lang = language
            self.save_user_language_setting()
            self.get_datetime()

    def go_back_to_settings_menu(self, menu_button) -> None:
        '''
        Purpose:
        - Go back to the settings menu.
        Parameters:
        - menu_button: The button that triggered the menu (MDFloatingActionButton).
        '''
        if self.languages:
            self.languages.dismiss()
        self.settings_menu(menu_button)

    def dismiss_current_menu(self, menu) -> None:
        '''
        Purpose:
        - Dismiss the current menu.
        Parameters:
        - menu: The menu to dismiss (MDDropdownMenu).
        '''
        if menu:
            menu.dismiss()

    def switch_palette(self, selected_palette) -> None:
        '''
        Purpose:
        - Switch the color palette of the application.
        Parameters:
        - selected_palette: The selected palette (str).
        '''
        self.theme_cls.primary_palette = selected_palette
    
    def switch_theme(self) -> None:
        '''
        Purpose:
        - Switch the theme of the application.
        '''
        self.theme_cls.theme_style = 'Dark' if self.theme_cls.theme_style == 'Light' else 'Light'

    def set_palette(self) -> None:
        '''
        Purpose:
        - Set the color palette of the application.
        '''
        instance_from_menu = self.get_instance_from_menu('Set Palette')
        available_palettes = [
            name_color.capitalize() for name_color in hex_colormap.keys()
        ]

        menu_items = [{'text': name_palette, 'on_release': lambda x=name_palette: self.switch_palette(x)} for name_palette in available_palettes]
        MDDropdownMenu(
            caller=instance_from_menu,
            items=menu_items,
        ).open()

    def get_instance_from_menu(self, name_item) -> MDDropdownMenu:
        '''
        Purpose:
        - Get the instance from the menu.
        Parameters:
        - name_item: The name of the item (str).
        Returns:
        - The instance from the menu.
        '''
        rv = self.settings.ids.md_menu
        index = next(i for i, data in enumerate(rv.data) if data['text'] == name_item)
        return rv.view_adapter.get_view(index, rv.data[0], rv.layout_manager.view_opts[index]['viewclass'])