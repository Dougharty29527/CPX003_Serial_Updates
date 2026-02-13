'''
Dropdown menu component module.
'''

# Kivy imports.
from kivy.clock import Clock
from kivymd.uix.menu import MDDropdownMenu

# Local imports.
from .base_widget import BaseWidget


class DropdownMenu(BaseWidget, MDDropdownMenu):
    '''
    DropdownMenu:
    - Class to set up the basic settings menu.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = None
        self.second_menu = None

    def open_menu(self, menu_button, items):
        '''
        Open the menu.
        '''
        self.dismiss_current_menu()
        menu_items = list(items)
        if self.app.user_access_level > 0:
            menu_items.append(
                {'text': f'{self.app.language_handler.translate("logout", "Logout")}', 'on_release': self.logout}
            )
        menu_items.append(
            {'text': f'{self.app.language_handler.translate("dismiss", "Dismiss")}', 'on_release': lambda: self.dismiss_current_menu(self.menu)}
        )
        self.menu = MDDropdownMenu(
            caller=menu_button,
            items=menu_items,
        )
        self.menu.open()

    def dismiss_current_menu(self, *args):
        '''
        Dismiss the current menu.
        '''
        if self.menu:
            self.menu.dismiss()

    def settings_menu(self, menu_button):
        '''
        Create the settings menu.
        '''
        settings_menu = [
            # {'text': f'{self.app.language_handler.translate("set_palette", "Set Palette")}', 'on_release': self.set_palette},
            {'text': f'{self.app.language_handler.translate("set_language", "Set Language")}', 'on_release': self.set_language},
            {'text': f'{self.app.language_handler.translate("time_entry", "Time Entry")}', 'on_release': self.time_selection}
            # {'text': f'{self.app.language_handler.translate("switch_theme", "Switch Theme")}', 'on_release': self.switch_theme},
            # {'text': f'{self.app.language_handler.translate("logout", "Logout")}', 'on_release': self.logout},
            # {'text': f'{self.app.language_handler.translate("dismiss", "Dismiss")}', 'on_release': lambda: self.dismiss_current_menu(self.menu)}        
        ]
        Clock.schedule_once(lambda dt: self.open_menu(menu_button, settings_menu))

    def switch_language(self, selected_language):
        '''
        Switch the language and go back to the settings menu.
        '''
        self.app.language_handler.switch_language(selected_language)
        self.second_menu.dismiss()
        self.menu.dismiss()


    def logout(self):
        '''
        Logout the user and go back to the login screen.
        '''
        self.dismiss_current_menu(self.menu)
        self.app.logout_dialog()

    def set_language(self):
        '''
        Set the language of the application.
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

    def get_instance_from_menu(self, name_item):
        '''
        Get the instance from the menu.
        '''
        rv = self.menu.ids.md_menu
        index = next(i for i, data in enumerate(rv.data) if data['text'] == name_item)
        return rv.view_adapter.get_view(index, rv.data[0], rv.layout_manager.view_opts[index]['viewclass'])

    def time_selection(self):
        '''
        Open the time selection screen and close the settings menu.
        '''
        self.dismiss_current_menu(self.menu)
        self.app.switch_screen('TimeEntry')
        
    def open_timezone_menu(self, caller, timezone_screen):
        '''
        Open timezone selection dropdown menu.
        '''
        # Common timezones
        common_timezones = [
            'UTC',
            'America/New_York',
            'America/Chicago',
            'America/Denver',
            'America/Los_Angeles',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Europe/Madrid',
            'Asia/Tokyo',
            'Australia/Sydney'
        ]
        
        menu_items = [
            {
                'text': tz,
                'on_release': lambda x=tz: self.select_timezone(timezone_screen, x)
            } for tz in common_timezones
        ]
        
        self.timezone_menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
        )
        self.timezone_menu.open()
        
    def select_timezone(self, timezone_screen, timezone):
        '''
        Select a timezone and update the display.
        '''
        timezone_screen.selected_timezone = timezone
        timezone_screen.update_time()
        self.timezone_menu.dismiss()

    # def switch_theme(self) -> None:
    #     '''
    #     Switch the theme of the application.
    #     '''
    #     if self.app.theme_cls.theme_style == 'Light':
    #         self.app.theme_cls.theme_style = 'Dark'
    #     else:
    #         self.app.theme_cls.theme_style = 'Light'

    # def switch_palette(self, selected_palette):
    #     '''
    #     Switch the color palette of the application.
    #     '''
    #     self.app.theme_cls.primary_palette = selected_palette

    # def set_palette(self) -> None:
    #     '''
    #     Set the color palette of the application.
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