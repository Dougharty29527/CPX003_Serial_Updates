#!/usr/bin/env python3
'''
Quick test script to read raw ADC values and display mapped pressure.
Run from the vst_gm_control_panel directory.

Usage: python3 test_pressure.py
Press Ctrl+C to exit.
'''

import board
import busio
import time
import sys

# Adafruit ADC imports
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


def map_value(x, in_min, in_max, out_min, out_max):
    '''Scale input value from one range to another.'''
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def convert_adc_to_pressure(adc_value, adc_zero=None):
    '''
    Convert raw ADC value to pressure.
    Uses adc_zero as the input minimum so calibration automatically zeros the sensor.
    
    Based on hardware calibration:
    - ADC 4080 = -31.35 pressure (low point)
    - ADC 26496 = 30.0 pressure (high point)
    - Slope: ~365.44 ADC units per pressure unit
    '''
    # Calculate slope from hardware calibration points
    adc1, pressure1 = 26496.0, 30.0
    adc2, pressure2 = 4080.0, -31.35
    adc_per_pressure = (adc1 - adc2) / (pressure1 - pressure2)  # ~365.44
    
    # If no calibration, use theoretical zero point
    if adc_zero is None:
        # Calculate theoretical ADC at 0 pressure from the two-point formula
        m = adc_per_pressure
        b = adc1 - m * pressure1
        adc_zero = b  # ~15533
    
    # Calculate adc_max based on desired pressure range (0 to 30.58)
    pressure_max = 30.58
    adc_max = adc_zero + (pressure_max * adc_per_pressure)
    
    # Map: adc_zero → 0.0, adc_max → pressure_max
    pressure = map_value(adc_value, adc_zero, adc_max, 0.0, pressure_max)
    return round(pressure, 2)


def main():
    print('Initializing I2C and ADC...')
    
    try:
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Initialize ADC (ADS1115)
        adc = ADS.ADS1115(i2c)
        
        # Pressure sensor is on channel P0
        channel = AnalogIn(adc, ADS.P0)
        
        print('ADC initialized successfully!')
        print('Reading pressure sensor on channel P0...')
        print('Press Ctrl+C to exit.')
        print('Press Enter to calibrate (set current reading as zero).\n')
        print('-' * 60)
        
    except Exception as e:
        print(f'Error initializing hardware: {e}')
        sys.exit(1)
    
    import select
    
    read_count = 0
    adc_zero = None  # No calibration by default
    
    try:
        while True:
            read_count += 1
            
            # Check for Enter key (non-blocking)
            if select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.readline()  # Consume the input
                # Calibrate - set current ADC as zero point
                adc_zero = channel.value
                print(f'\n*** CALIBRATED! adc_zero set to {adc_zero} ***')
                print('-' * 60)
            
            # Read raw ADC value
            raw_adc = channel.value
            
            # Convert to pressure (with calibration if set)
            raw_pressure = convert_adc_to_pressure(raw_adc)
            cal_pressure = convert_adc_to_pressure(raw_adc, adc_zero) if adc_zero else raw_pressure
            
            # Display (overwrite same line) with counter
            cal_str = f'{cal_pressure:7.2f}' if adc_zero else '   N/A '
            output = f'[{read_count:5d}] ADC: {raw_adc:6d} | RAW: {raw_pressure:7.2f} | CAL: {cal_str} IWC'
            sys.stdout.write(f'\r{output}')
            sys.stdout.flush()
            
            # Small delay between readings
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print('\n\nExiting...')
        if adc_zero:
            print(f'Final calibration value (adc_zero): {adc_zero}')
        sys.exit(0)


if __name__ == '__main__':
    main()
