'''
Status bar component module.
'''

# Kivy imports.
from kivymd.app import MDApp
from kivymd.uix.card import MDCard

# Local imports.
from .base_widget import BaseWidget


class StatusBar(BaseWidget, MDCard):
    ''' 
    StatusBar:
    - Class to manage status updates.
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_kv_post(self, widget):
        '''
        Initialize the widget.
        '''
        self.app = MDApp.get_running_app()
        self.style = 'elevated'
        self._default_color = None  # Store default color for restoration
    
    def set_hardware_error_state(self, is_error):
        '''
        Set the status bar to error state (red) when hardware is disconnected.
        
        Args:
            is_error (bool): True to show red error state, False to restore normal
        '''
        if is_error:
            # Store default color if not already stored
            if self._default_color is None and hasattr(self, 'md_bg_color'):
                self._default_color = self.md_bg_color
            # Set to red error color
            self.md_bg_color = [0.8, 0.2, 0.2, 1]  # Red color for hardware error
        else:
            # Restore default color
            if self._default_color is not None:
                self.md_bg_color = self._default_color
            else:
                # Fallback to theme color if no default was stored
                if hasattr(self.app, 'theme_cls'):
                    self.md_bg_color = self.app.theme_cls.surfaceColor

    def on_leave(self, *args):
        '''
        Remove on_leave animations.
        '''
        pass

    def on_press(self, *args):
        '''
        Remove on_press animations.
        '''
        pass

    def on_release(self, *args):
        '''
        Remove on_release animations.
        '''
        pass

    def on_touch_move(self, touch):
        '''
        Prevent touch move events.
        '''
        pass
