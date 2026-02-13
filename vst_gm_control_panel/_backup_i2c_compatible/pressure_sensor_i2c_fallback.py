#!/usr/bin/env python3
'''
Pressure sensor module for handling pressure reading and calibration functionality.
'''

# Standard imports
from collections import deque  # For circular buffer of pressure readings

# Third-party imports
import adafruit_ads1x15.ads1115 as ADS  # ADC driver for pressure sensor
from adafruit_ads1x15.analog_in import AnalogIn  # Analog input channel
from kivy.logger import Logger  # Logging system
from kivymd.app import MDApp  # Main app reference


class PressureSensor:
    '''
    Pressure sensor controller for ADC-based pressure readings.
    Supports graceful degradation when hardware is unavailable.
    '''

    def __init__(self, adc, mock_mode=False):
        self.app = MDApp.get_running_app()
        self.mock_mode = mock_mode
        self._adc = adc
        
        # Initialize hardware channel or mock channel
        if not self.mock_mode and self._adc is not None:
            try:
                self._channel = AnalogIn(self._adc, ADS.P0)
            except Exception as e:
                Logger.warning(f'PressureSensor: Failed to initialize ADC channel, using mock mode: {e}')
                self.mock_mode = True
                self._channel = None
        else:
            self._channel = None
            
        self.adc_zero = self.get_adc_zero()
        self.pressure_readings = deque(maxlen=60)  # Buffer for pressure readings (2 seconds)
        self.sensor_dc_value = -99.9  # Default sensor disconnect error value

    @staticmethod
    def map_value(x, in_min, in_max, out_min, out_max):
        '''
        Scale input value from one range to another 
        '''
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def _calculate_average(self, readings):
        '''
        Calculate the average of the readings
        '''
        if not readings:
            return self.sensor_dc_value
        valid_readings = [r for r in readings if r != self.sensor_dc_value]
        if valid_readings:
            if len(valid_readings) > 2:
                readings = sorted(valid_readings)  # Sort to identify extremes
                return sum(readings[1:-1]) / (len(readings) - 2)  # Average without min/max
            return sum(valid_readings) / len(valid_readings)
        return self.sensor_dc_value

    def get_adc_zero(self):
        '''
        Get the ADC zero value
        '''
        adc_zero = self.app.gm_db.get_setting('adc_zero')
        if adc_zero is None:
            adc_zero = 15422.0  # Factory default ADC zero point
            self.app.gm_db.add_setting('adc_zero', adc_zero)  # Save to database
        return float(adc_zero)  # Ensure float type for calculations

    def _read_adc_value(self):
        '''
        Read raw ADC value with basic error handling.
        Returns error value in mock mode.
        '''
        # Return error value in mock mode to indicate hardware disconnection
        if self.mock_mode or self._channel is None:
            return self.sensor_dc_value  # -99.9 indicates hardware not connected
            
        try:
            value = self._channel.value
            if value is None or value == 0:
                return self.sensor_dc_value
            pressure = self._convert_adc_to_pressure(value)
            return pressure if float(pressure) > -40 else self.sensor_dc_value
        except IOError as e:
            Logger.debug(f'PressureSensor: IOError reading ADC value {e}')
            return self.sensor_dc_value

    def _collect_pressure_samples(self, adc_samples=30):
        '''
        Collect multiple pressure samples while avoiding relay noise
        '''
        for _ in range(adc_samples):
            if self._check_mcp_engaged():  # Skip if relays are engaged
                continue
            pressure = self._read_adc_value()
            # if pressure is None:
            #     pressure = self.validate_pressure_reading()
            self.pressure_readings.append(pressure)

    def validate_pressure_reading(self, max_attempts=15):
        '''
        Attempt to get a valid pressure reading with retry logic
        '''
        validation_count = 0
        for _ in range(max_attempts):
            try:
                pressure = self._read_adc_value()
                if pressure is not None:
                    return pressure   
                validation_count += 1
            except IOError as e:
                Logger.debug(f'PressureSensor: IOError during pressure validation: {e}')
                validation_count += 1
            if validation_count >= max_attempts:
                Logger.debug('PressureSensor: Max validation attempts reached, returning sensor disconnect value')
                return -99.9
        Logger.debug('PressureSensor: Unable to get valid pressure reading, returning sensor disconnect value')
        return -99.9

    def _convert_adc_to_pressure(self, adc_value):
        '''
        Convert raw ADC value to pressure reading using direct linear formula.
        
        Based on hardware calibration:
        - ADC 4080 = -31.35 pressure (low point)
        - ADC 26496 = 30.0 pressure (high point)
        - Slope (m): ~365.44 ADC units per pressure unit
        
        Formula: pressure = (adc_value - adc_zero) / m
        '''
        # Fixed slope from hardware calibration points
        adc1, pressure1 = 26496.0, 30.0
        adc2, pressure2 = 4080.0, -31.35
        m = (adc1 - adc2) / (pressure1 - pressure2)  # ~365.44
        
        # Direct linear formula: pressure = (adc_value - adc_zero) / m
        pressure = (adc_value - self.adc_zero) / m
        return round(pressure, 2)

    def _check_mcp_engaged(self):
        '''
        Check if MCP I2C lock is held (relays being operated)
        '''
        try:
            if hasattr(self.app.io, '_mcp_lock'):
                return self.app.io._mcp_lock.locked()
            return False
        except Exception as e:
            Logger.debug(f'PressureSensor: Error checking MCP lock status: {e}')
            return False

    def get_pressure(self, _retry_count=0):
        '''
        Get pressure readings with limited retries to prevent blocking.
        '''
        max_retries = 3
        try:
            self._collect_pressure_samples()
            if self.pressure_readings is None or len(self.pressure_readings) == 0:
                return self.sensor_dc_value
            avg_pressure = self._calculate_average(self.pressure_readings)
            if avg_pressure is None or float(avg_pressure) <= -40:
                return self.sensor_dc_value
            return self._format_pressure_result(avg_pressure)  
        except IOError as e:
            Logger.debug(f'PressureSensor: IOError while reading pressure (attempt {_retry_count + 1}): {e}')
            if _retry_count < max_retries:
                return self.get_pressure(_retry_count=_retry_count + 1)
            Logger.warning(f'PressureSensor: Max retries reached, returning error value')
            return self.sensor_dc_value

    def _format_pressure_result(self, avg_pressure):
        '''
        Format the final pressure result
        '''
        if avg_pressure is None or float(avg_pressure) <= -40:
            return self.sensor_dc_value
        formatted = f'{avg_pressure:.2f}'  # Format to 2 decimal places    
        # Convert -0.00 to 0.00 for better display
        return '0.00' if formatted == '-0.00' else formatted

    def calibrate(self):
        '''
        Calibrate the pressure sensor using averaged sampling.
        Collects 30 samples and uses trimmed mean (removes 3 highest/lowest).
        Returns default value in mock mode.
        '''
        # Return default calibration in mock mode
        if self.mock_mode or self._channel is None:
            Logger.info('PressureSensor: Mock mode - returning default calibration')
            return 15422.0
        
        # Collect 30 ADC samples for stable calibration
        samples = []
        for _ in range(30):
            try:
                value = self._channel.value
                if value is not None and value != 0:
                    samples.append(value)
            except IOError:
                continue
        
        # Calculate trimmed mean (remove 3 highest and 3 lowest)
        if len(samples) >= 7:
            samples.sort()
            trimmed = samples[3:-3]
            self.adc_zero = sum(trimmed) / len(trimmed)
        elif samples:
            self.adc_zero = sum(samples) / len(samples)
        else:
            Logger.debug('PressureSensor: No valid samples during calibration')
            self.adc_zero = 15422.0  # Fall back to default
        
        self.pressure_readings.clear()
        
        if self.adc_zero < -40 or self.adc_zero == 0:
            Logger.debug(f'PressureSensor: Invalid ADC zero value during calibration: {self.adc_zero}')
            self.adc_zero = 15422.0  # Fall back to default instead of error value
        
        try:
            self.app.gm_db.add_setting('adc_zero', self.adc_zero)
            Logger.debug(f'PressureSensor: Calibrated ADC zero value: {self.adc_zero}')
        except ValueError as e:
            Logger.debug(f'PressureSensor: Error saving ADC zero value during calibration: {e}')
        return self.adc_zero