'''
Faults & Alarms Screen
'''

# Standard imports.
from datetime import datetime

# Kivy imports.
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout


class FaultsScreen(MDScreen):
    '''
    Faults & Alarms Screen:
    - This class sets up the Faults & Alarms screen.
    '''

    # Define StringProperty for each alarm.
    pressure_sensor_status = StringProperty('NORMAL')
    vac_pump_status = StringProperty('NORMAL')
    overfill_status = StringProperty('NORMAL')
    digital_storage_status = StringProperty('NORMAL')
    under_pressure_status = StringProperty('NORMAL')
    over_pressure_status = StringProperty('NORMAL')
    zero_pressure_status = StringProperty('NORMAL')
    variable_pressure_status = StringProperty('NORMAL')
    seventy_two_hour_shutdown_status = StringProperty('NORMAL')
    gm_fault_status = StringProperty('NORMAL')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.alarms = self.app.profile_handler.get_alarms()
        self.build_alarm_screen()
        Clock.schedule_interval(self.check_and_update_alarms, 3)
        # Bind to both theme changes and profile changes
        self.app.bind(
            theme_cls=self.update_alarm_screen,
            profile=self.on_profile_changed
        )

    def on_profile_changed(self, instance, value):
        """Handle profile changes by rebuilding the alarm screen"""
        # Update alarms list for new profile
        self.alarms = self.app.profile_handler.get_alarms()
        # Rebuild screen with new alarms
        self.build_alarm_screen()

    def build_alarm_screen(self, *args):
        '''
        Purpose:
        - Build the alarms screen.
        '''
        # Clear existing alarms
        self.ids.alarms_list.clear_widgets()

        for alarm in self.alarms:
            try:
                alarm_key = self._normalize_alarm_name(alarm)
                alarm_str = self.app.language_handler.translate(alarm_key, alarm_key)
                primary_container = self._create_primary_container(alarm_key)
                alarm_label = self._create_alarm_label(alarm_str)
                alarm_status_label = self._create_alarm_status_label(alarm_key)

                # Bind the StringProperty to the MDLabel text.
                self.bind(**{f'{alarm_key}_status': self._create_bind_callback(alarm_status_label)})

                alarm_container = self._create_sub_container()
                alarm_status_container = self._create_status_sub_container()

                alarm_container.add_widget(alarm_label)
                alarm_status_container.add_widget(alarm_status_label)
                primary_container.add_widget(alarm_container)
                primary_container.add_widget(alarm_status_container)
                self.ids.alarms_list.add_widget(primary_container)

            except AttributeError as e:
                pass
            except Exception as e:
                raise

    def _normalize_alarm_name(self, alarm):
        '''
        Normalize alarm name to match the attribute naming convention.
        '''
        return alarm.lower().replace(' ', '_').replace('72_hour_shutdown', 'seventy_two_hour_shutdown')

    def _create_primary_container(self, alarm_key):
        '''
        Create the primary container for alarms.
        '''
        container = MDBoxLayout(
            theme_bg_color='Custom',
            md_bg_color=self.app.success_color,
            adaptive_height=True,
            size_hint_x=None,
            width=450,
            orientation='horizontal',
            radius='5dp',
            padding=['21dp', '2dp', '21dp', '2dp']
        )
        container.alarm_key = alarm_key
        return container

    def _create_sub_container(self):
        '''
        Create sub-container for alarm label and status.
        '''
        return MDBoxLayout(
            adaptive_height=True,
            size_hint_x=.8
        )

    def _create_alarm_label(self, alarm_str):
        '''
        Create the alarm label.
        '''
        return MDLabel(
            text=alarm_str.upper(),
            theme_font_size='Custom',
            font_size='19sp',
            theme_text_color='Custom',
            text_color=self.app.theme_cls.onSurfaceColor,
            adaptive_size=True,
            halign='center'
        )

    def _create_status_sub_container(self):
        '''
        Create sub-container for alarm label and status.
        '''
        return MDBoxLayout(
            adaptive_height=True,
            size_hint_x=.2
        )

    def _create_alarm_status_label(self, alarm_key):
        '''
        Create the alarm status label.
        '''
        return MDLabel(
            text=getattr(self, f'{alarm_key}_status'),
            theme_font_size='Custom',
            font_size='19sp',
            theme_text_color='Custom',
            text_color=self.app.theme_cls.secondaryColor,
            adaptive_size=True,
            halign='right'
        )

    def _create_bind_callback(self, alarm_status):
        '''
        Purpose:
        - Create a bind callback for the StringProperty of the alarm status.
        '''
        return lambda instance, value: setattr(alarm_status, 'text', value)

    def update_alarm_screen(self, *args):
        '''
        Purpose:
        - Update the alarms screen when the language or theme is switched.
        '''
        try:
            self.alarms = self.app.profile_handler.get_alarms()
            self.build_alarm_screen()
        except Exception as e:
            pass

    def check_and_update_alarms(self, *args):
        '''
        Purpose:
        - Check and update status of alarms.
        '''
        for alarm in self.alarms:
            alarm_key = self._normalize_alarm_name(alarm)
            if alarm_key in self.app.alarm_list:
                alarm_status_str = self.app.language_handler.translate('alarm', 'ALARM').upper()
                self.update_container_color(alarm_key, True)
            else:
                alarm_status_str = 'NORMAL'
                self.update_container_color(alarm_key, False)
            setattr(self, f'{alarm_key}_status', alarm_status_str)
            if self.app.shutdown:
                alarm_key = 'seventy_two_hour_shutdown'
                self.seventy_two_hour_shutdown_status = self.app.language_handler.translate('alarm', 'ALARM').upper()
                self.update_container_color('seventy_two_hour_shutdown', True)

    def update_container_color(self, alarm_key, is_alarm):
        '''
        Purpose:
        - Update the background color of the primary container based on alarm status.
        '''
        for child in self.ids.alarms_list.children:
            if hasattr(child, 'alarm_key') and child.alarm_key == alarm_key:
                if is_alarm:
                    child.md_bg_color = self.app.theme_cls.onErrorColor
                else:
                    child.md_bg_color = self.app.success_color