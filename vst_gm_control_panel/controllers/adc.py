#!./venv/bin/python

'''
===========================================================
                    Pressure Sensor
===========================================================
'''

from collections import deque
from utils import (
    Logger,
    DatabaseManager
)
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


class PressureSensor:
    '''
    Pressure Sensor
    ---------------
    This class is used to handle the pressure sensor.
    '''
    _logger = Logger(__name__)
    log = _logger.log_message
    _hardware_available = False
    _warnings_logged = {'board': False, 'busio': False, 'ads': False}
    _database = DatabaseManager()

    def __init__(self, adc_zero=15422.0, gain=1):
        self.db = self._database.gm()
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self._adc = ADS.ADS1115(self.i2c)
        self._channel = AnalogIn(self._adc, ADS.P0)
        self._adc.gain = gain
        self.adc_zero = float(self.db.get_setting('adc_zero')) if self.db.get_setting('adc_zero') is not None else adc_zero
        self.pressure_readings = deque(maxlen=60)

    @staticmethod
    def _calculate_average(readings):
        ''' Calculate the average of the readings. '''
        if len(readings) > 2:
            readings = sorted(readings)
            return sum(readings[1:-1]) / (len(readings) - 2)
        return sum(readings) / len(readings)

    @staticmethod
    def map_value(x, in_min, in_max, out_min, out_max):
        ''' Map a value from one range to another. '''
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def get_pressure(self) -> str:
        ''' Get the pressure reading from the sensor. '''
        # if not self._hardware_available:
        #     return '-99.9'
        try:
            for _ in range(30):
                value = self._channel.value
                pressure = round(self.map_value(value, self.adc_zero, 22864.0, 0.0, 20.8), 2)
                self.pressure_readings.append(pressure)
            avg_pressure = self._calculate_average(self.pressure_readings)
            return f'{avg_pressure:.2f}' if f'{avg_pressure:.2f}' != '-0.00' else '0.00'
        except IOError as e:
            self.log('error', f'Error reading from ADC: {e}')
            return '-99.9'

    def calibrate(self):
        ''' Recalibrate the pressure sensor. '''
        if not self._hardware_available:
            return 'ERR'
        self.adc_zero = self._channel.value
        self.pressure_readings.clear()
        try:
            self.db.add_setting('adc_zero', self.adc_zero)
        except ValueError as e:
            self.log('warning', f'{e}')
        return self.adc_zero


class PressureThresholds:
    '''
    Pressure Thresholds
    -------------------
    This class is used to store and update the pressure thresholds for the application.
    '''

    def __init__(self, low=-6.00, high=2.00, zero=0.15, variable=0.20):
        self.low = low
        self.high = high
        self.zero = zero
        self.variable = variable

    def set_low(self, value):
        ''' Set the low pressure threshold. '''
        self.low = value

    def set_high(self, value):
        ''' Set the high pressure threshold. '''
        self.high = value

    def set_zero(self, value):
        ''' Set the zero pressure threshold. '''
        self.zero = value

    def set_variable(self, value):
        ''' Set the variable pressure threshold. '''
        self.variable = value

    def __str__(self):
        return f'Thresholds(low={self.low}, high={self.high}, zero={self.zero}, variable={self.variable})'
