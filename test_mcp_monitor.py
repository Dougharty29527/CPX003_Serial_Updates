#!/usr/bin/env python3
'''
MCP23017 Live Pin Monitor

Monitors all MCP23017 pins in real-time and displays state changes as they occur.
Uses the same pin naming convention as the main application.

Usage:
    python test_mcp_monitor.py              # Monitor with default settings
    python test_mcp_monitor.py -i 50        # Poll every 50ms
    python test_mcp_monitor.py --no-color   # Disable color output
    python test_mcp_monitor.py -q           # Quiet mode (skip initial status)

Press Ctrl+C to exit.
'''

import argparse
import sys
import time
from datetime import datetime

try:
    import board
    import busio
    from digitalio import Direction
    from adafruit_mcp230xx.mcp23017 import MCP23017
except ImportError as e:
    print(f'Error: Missing required library: {e}')
    print('Make sure you are running from the venv with required dependencies.')
    sys.exit(1)


# Pin mapping with direction (same as io_manager.py)
PIN_MAP = {
    'motor': (0, 'output'),
    'v1': (1, 'output'),
    'v2': (2, 'output'),
    'v5': (3, 'output'),
    'shutdown': (4, 'output'),
    'tls': (8, 'input'),
    'panel_power': (10, 'input')
}

# ANSI color codes
COLORS = {
    'green': '\033[92m',
    'red': '\033[91m',
    'yellow': '\033[93m',
    'cyan': '\033[96m',
    'reset': '\033[0m',
    'bold': '\033[1m'
}


def colorize(text, color, use_color=True):
    '''Apply ANSI color to text if colors are enabled.'''
    if not use_color:
        return text
    return f'{COLORS.get(color, "")}{text}{COLORS["reset"]}'


def init_hardware():
    '''Initialize I2C bus and MCP23017.'''
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        mcp = MCP23017(i2c)
        return mcp
    except Exception as e:
        print(f'Error initializing hardware: {e}')
        sys.exit(1)


def setup_pins(mcp):
    '''Configure all pins and return pin objects with their states.'''
    pins = {}
    for name, (pin_num, direction) in PIN_MAP.items():
        pin = mcp.get_pin(pin_num)
        if direction == 'output':
            pin.direction = Direction.OUTPUT
        else:
            pin.direction = Direction.INPUT
        pins[name] = pin
    return pins


def get_timestamp():
    '''Get current timestamp in HH:MM:SS.mmm format.'''
    now = datetime.now()
    return now.strftime('%H:%M:%S.') + f'{now.microsecond // 1000:03d}'


def format_state(value, use_color=True):
    '''Format pin state as ON/OFF with optional color.'''
    if value:
        return colorize('ON ', 'green', use_color)
    else:
        return colorize('OFF', 'red', use_color)


def show_initial_status(pins, use_color=True):
    '''Display current state of all pins.'''
    print(colorize('\nCurrent Pin States:', 'bold', use_color))
    print('-' * 40)
    
    # Show outputs first, then inputs
    print(colorize('  Outputs:', 'cyan', use_color))
    for name in ['motor', 'v1', 'v2', 'v5', 'shutdown']:
        state = format_state(pins[name].value, use_color)
        pin_num = PIN_MAP[name][0]
        print(f'    {name:12} (pin {pin_num:2}): {state}')
    
    print(colorize('  Inputs:', 'cyan', use_color))
    for name in ['tls', 'panel_power']:
        state = format_state(pins[name].value, use_color)
        pin_num = PIN_MAP[name][0]
        print(f'    {name:12} (pin {pin_num:2}): {state}')
    
    print('-' * 40)
    print()


def monitor_pins(pins, interval_ms, use_color=True):
    '''Main monitoring loop - detect and display pin changes.'''
    # Store previous states
    prev_states = {name: pin.value for name, pin in pins.items()}
    
    interval_sec = interval_ms / 1000.0
    change_count = 0
    
    print(colorize('Monitoring for pin changes...', 'yellow', use_color))
    print(f'Poll interval: {interval_ms}ms')
    print('Press Ctrl+C to exit.\n')
    
    try:
        while True:
            for name, pin in pins.items():
                current_state = pin.value
                prev_state = prev_states[name]
                
                if current_state != prev_state:
                    change_count += 1
                    timestamp = get_timestamp()
                    
                    old_str = format_state(prev_state, use_color)
                    new_str = format_state(current_state, use_color)
                    
                    pin_type = PIN_MAP[name][1]
                    type_indicator = colorize(f'[{pin_type[0].upper()}]', 'cyan', use_color)
                    
                    print(f'[{timestamp}] {type_indicator} {name:12}: {old_str} -> {new_str}')
                    
                    prev_states[name] = current_state
            
            time.sleep(interval_sec)
            
    except KeyboardInterrupt:
        print(f'\n\nMonitoring stopped. Total changes detected: {change_count}')
        return


def main():
    parser = argparse.ArgumentParser(
        description='Monitor MCP23017 pins for state changes in real-time.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python test_mcp_monitor.py              Monitor with default settings (100ms interval)
  python test_mcp_monitor.py -i 50        Poll every 50ms for faster detection
  python test_mcp_monitor.py --no-color   Disable color output
  python test_mcp_monitor.py -q           Skip initial status display

Pin types in output:
  [O] = Output pin (motor, v1, v2, v5, shutdown)
  [I] = Input pin (tls, panel_power)
        '''
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=100,
        help='Polling interval in milliseconds (default: 100)'
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable color output'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Skip initial status display'
    )
    
    args = parser.parse_args()
    use_color = not args.no_color
    
    print(colorize('MCP23017 Pin Monitor', 'bold', use_color))
    print('=' * 40)
    
    # Initialize hardware
    print('Initializing I2C and MCP23017...')
    mcp = init_hardware()
    pins = setup_pins(mcp)
    print('Hardware initialized successfully!')
    
    # Show initial status unless quiet mode
    if not args.quiet:
        show_initial_status(pins, use_color)
    
    # Start monitoring
    monitor_pins(pins, args.interval, use_color)


if __name__ == '__main__':
    main()
