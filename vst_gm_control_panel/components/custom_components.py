'''
This module is for altered/customized Kivy components.
'''

# Kivy imports.
from kivymd.app import MDApp
from kivy.logger import Logger
from kivy.properties import StringProperty
from kivymd.uix.bottomsheet import MDBottomSheet
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog, MDDialogContentContainer, MDDialogHeadlineText,
    MDDialogSupportingText, MDDialogButtonContainer
)
from kivymd.uix.navigationdrawer import MDNavigationDrawerItem
from kivy.uix.widget import Widget

# Local imports.
from .base_widget import BaseWidget


class BaseDialog(MDDialog):
    '''
    BaseDialog:
    - Base class for all custom dialogs with shared functionality.
    - Handles common initialization, animation removal, and singleton pattern.
    '''
    _current_dialog = None

    def on_kv_post(self, base_widget):
        '''Initialize the dialog with app reference and theme colors.'''
        self.app = MDApp.get_running_app()
        self.theme_bg_color = 'Custom'
        self.md_bg_color = self.app.theme_cls.surfaceColor

    def on_leave(self, *args):
        '''Remove on_leave animations.'''
        pass

    def on_press(self, *args):
        '''Remove on_press animations.'''
        pass

    def on_release(self, *args):
        '''Remove on_release animations.'''
        pass

    @classmethod
    def dismiss_current_dialog(cls):
        '''Dismiss the currently open dialog if one exists.'''
        if cls._current_dialog is not None:
            cls._current_dialog.dismiss()
            cls._current_dialog = None

    def _prepare_dialog(self):
        '''Prepare dialog for opening by dismissing existing dialog.'''
        self.__class__.dismiss_current_dialog()
        self.__class__._current_dialog = self

    def _handle_dialog_close(self, accept_method=None):
        '''Handle dialog cleanup and execute accept method if provided.'''
        if accept_method:
            try:
                accept_method()
            except Exception as e:
                Logger.error(f'{self.__class__.__name__}: Error in accept method: {e}')
        self.__class__._current_dialog = None
        self.dismiss()


class CustomDialog(BaseDialog):
    '''CustomDialog: Class to manage custom dialogs.'''

    def open_dialog(
        self,
        title,
        text=None,
        accept=None,
        accept_method=None,
        cancel=None
    ):
        '''
        Open a dialog box.
        - title: str
        - text: str (optional)
        - accept: str (optional)
        '''
        title_widget = MDDialogHeadlineText(text=title)
        text_widget = MDDialogSupportingText(text=text)

        if not callable(accept_method):
            accept_method = lambda: None

        buttons = [Widget()]
        if accept:
            accept_btn = MDButton(
                MDButtonText(text=accept),
                style='text',
                radius='5dp',
                on_release=lambda x: (accept_method(), self.dismiss())
            )
            buttons.append(accept_btn)

        if cancel:
            cancel_btn = MDButton(
                MDButtonText(text=cancel),
                style='text',
                radius='5dp',
                on_release=lambda x: self.dismiss()
            )
            buttons.append(cancel_btn)

        button_container = MDDialogButtonContainer(*buttons, spacing='8dp')

        for widget in [title_widget, text_widget, MDDialogContentContainer(), button_container]:
            self.add_widget(widget)

        self.open()


class TimeoutDialog(BaseDialog):
    '''
    TimeoutDialog:
    - Class to manage timeout dialogs.
    - Ensures only one timeout dialog is shown at a time.
    '''
    _current_dialog = None

    def open_dialog(self, accept_method, cancel_method):
        '''Open the timeout dialog box. Dismisses any existing dialog first.'''
        self._prepare_dialog()

        title_text = self.app.language_handler.translate('session_timeout', 'Session Timeout')
        text_start = self.app.language_handler.translate(
            'timeout_message', 'Your session has timed out due to inactivity.'
        )
        text_end = self.app.language_handler.translate(
            'timeout_confirmation', 'What would you like to do next?'
        )
        text_full = f'{text_start}\n\n{text_end}'
        code_entry_text = self.app.language_handler.translate('re_enter_code', 'Re-enter Code')
        cancel_text = self.app.language_handler.translate('cancel', 'Cancel')

        title = MDDialogHeadlineText(text=title_text)
        text = MDDialogSupportingText(text=text_full)

        if not callable(accept_method):
            accept_method = lambda: None

        accept = MDButton(
            MDButtonText(text=code_entry_text),
            style='text',
            radius='5dp',
            on_release=lambda x: (accept_method(), self.dismiss())
        )

        cancel = MDButton(
            MDButtonText(text=cancel_text),
            style='text',
            radius='5dp',
            on_release=lambda x: (cancel_method(), self.dismiss())
        )

        button_container = MDDialogButtonContainer(Widget(), accept, cancel, spacing='8dp')

        for widget in [title, text, MDDialogContentContainer(), button_container]:
            self.add_widget(widget)

        self.open()


class ConfirmationDialog(BaseDialog):
    '''
    ConfirmationDialog:
    - Class to manage custom confirmation dialogs.
    - Ensures only one confirmation dialog is shown at a time.
    '''
    _current_dialog = None

    def update_title(self, new_title):
        self.title_label.text = new_title

    def open_dialog(self, title, text, accept, accept_method=None):
        '''Open a dialog box. Dismisses any existing dialog first.'''
        self._prepare_dialog()

        title_widget = MDDialogHeadlineText(text=title)
        text_widget = MDDialogSupportingText(text=text)

        acknowledge = MDButton(
            MDButtonText(text=accept, pos_hint={'center_x': .5}),
            style='text',
            radius='2dp',
            on_release=lambda x: self._handle_dialog_close(accept_method)
        )
        button_container = MDDialogButtonContainer(Widget(), acknowledge, spacing='8dp')

        for widget in [title_widget, text_widget, MDDialogContentContainer(), button_container]:
            self.add_widget(widget)

        self.open()


class AlarmDialog(BaseDialog):
    '''
    AlarmDialog:
    - Class to manage alarm dialogs with countdown timer.
    - Ensures only one alarm dialog is shown at a time.
    '''
    time_remaining = StringProperty('')
    _current_dialog = None

    def on_kv_post(self, base_widget):
        '''Initialize with app binding for shutdown timer.'''
        super().on_kv_post(base_widget)
        self.app.bind(shutdown_time_remaining=self.setter('time_remaining'))

    def open_dialog(self, title, text, accept, accept_method=None):
        '''Open a dialog box. Dismisses any existing dialog first.'''
        self._prepare_dialog()

        title_label = MDDialogHeadlineText()
        title_label.text = f'{title} {self.time_remaining}'
        self.bind(time_remaining=lambda instance, value: setattr(title_label, 'text', f'{title} {value}'))
        text_label = MDDialogSupportingText(text=text)

        acknowledge = MDButton(
            MDButtonText(text=accept, pos_hint={'center_x': .5}),
            style='text',
            radius='2dp',
            on_release=lambda x: self._handle_dialog_close(accept_method)
        )
        button_container = MDDialogButtonContainer(Widget(), acknowledge, spacing='8dp')

        for widget in [title_label, text_label, MDDialogContentContainer(), button_container]:
            self.add_widget(widget)

        self.open()


class LogoutDialog(BaseDialog):
    '''
    LogoutDialog:
    - Class to manage logout confirmation dialogs.
    - Ensures only one logout dialog is shown at a time.
    '''
    _current_dialog = None

    def open_dialog(self, accept_method):
        '''Open the logout dialog box. Dismisses any existing dialog first.'''
        self._prepare_dialog()

        title_full = self.app.language_handler.translate('logout', 'Log Out?')
        text_start = self.app.language_handler.translate(
            'logout_confirmation', 'Are you sure you want to log out?'
        )
        text_end = self.app.language_handler.translate(
            'logout_confirmation_two', 'You will be redirected to the Main screen.'
        )
        text_full = f'{text_start}\n{text_end}'
        accept_text = self.app.language_handler.translate('accept', 'Accept')
        cancel_text = self.app.language_handler.translate('cancel', 'Cancel')

        title = MDDialogHeadlineText(text=title_full)
        text = MDDialogSupportingText(text=text_full)

        if not callable(accept_method):
            accept_method = lambda: None

        accept = MDButton(
            MDButtonText(text=accept_text),
            style='text',
            radius='5dp',
            on_release=lambda x: (accept_method(), self.dismiss())
        )

        cancel = MDButton(
            MDButtonText(text=cancel_text),
            style='text',
            radius='5dp',
            on_release=lambda x: self.dismiss()
        )

        button_container = MDDialogButtonContainer(Widget(), accept, cancel, spacing='8dp')

        for widget in [title, text, MDDialogContentContainer(), button_container]:
            self.add_widget(widget)

        self.open()


class NavDrawerItem(BaseWidget, MDNavigationDrawerItem):
    '''
    - Remove on release from button press.
    '''
    def on_release(self, *args) -> None:
        '''
        Fired when the item is released
        (i.e. the touch/click that pressed the item goes away).
        '''
        self.selected = not self.selected


class NoDragMDBottomSheet(MDBottomSheet):
    '''
    Disable dragging on the bottom sheet.
    '''
    def on_touch_move(self, touch):
        return False