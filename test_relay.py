#!/usr/bin/env python3
'''
Relay Toggle CLI Test Script

Toggle individual relays by name or set predefined modes using command-line arguments.
Uses the same relay naming convention as the main application.

Usage:
    python test_relay.py -v1        # Toggle v1 relay
    python test_relay.py -motor     # Toggle motor relay
    python test_relay.py -v2        # Toggle v2 relay
    python test_relay.py -v5        # Toggle v5 relay
    python test_relay.py -shutdown  # Toggle shutdown relay
    python test_relay.py --status   # Show current state of all relays
    python test_relay.py -v1 --on   # Explicitly turn v1 ON
    python test_relay.py -v1 --off  # Explicitly turn v1 OFF
    
    # Mode options (sets multiple relays at once)
    python test_relay.py -run       # Set run mode (motor, v1, v5 ON)
    python test_relay.py -rest      # Set rest mode (all OFF)
    python test_relay.py -purge     # Set purge mode (motor, v2 ON)
    python test_relay.py -burp      # Set burp mode (v5 ON)
    python test_relay.py -bleed     # Set bleed mode (v2, v5 ON)
    python test_relay.py -leak      # Set leak mode (v1, v2, v5 ON)
    python test_relay.py --reset    # Turn all relays OFF
    
    # Full cycle options
    python test_relay.py --cycle       # Run standard cycle (~7m 47s)
    python test_relay.py --quick-cycle # Run quick test cycle (~1m 29s)
'''

import argparse
import sys
import time

try:
    import board
    import busio
    from digitalio import Direction
    from adafruit_mcp230xx.mcp23017 import MCP23017
except ImportError as e:
    print(f'Error: Missing required library: {e}')
    print('Make sure you are running from the venv with required dependencies.')
    sys.exit(1)


# Pin mapping (same as io_manager.py)
PIN_MAP = {
    'motor': 0,
    'v1': 1,
    'v2': 2,
    'v5': 3,
    'shutdown': 4
}

# Mode configurations (same as io_manager.py)
MODE_CONFIG = {
    'run': {'motor': True, 'v1': True, 'v2': False, 'v5': True},
    'rest': {'motor': False, 'v1': False, 'v2': False, 'v5': False},
    'purge': {'motor': True, 'v1': False, 'v2': True, 'v5': False},
    'burp': {'motor': False, 'v1': False, 'v2': False, 'v5': True},
    'bleed': {'motor': False, 'v1': False, 'v2': True, 'v5': True},
    'leak': {'motor': False, 'v1': True, 'v2': True, 'v5': True}
}

# Cycle timing configurations (in seconds)
STANDARD_TIMING = {
    'run_time': 120,
    'purge_time': 50,
    'burp_time': 5,
    'rest_time': 2,
    'final_rest': 15
}

QUICK_TIMING = {
    'run_time': 10,
    'purge_time': 10,
    'burp_time': 2,
    'rest_time': 2,
    'final_rest': 5
}


def init_hardware():
    '''Initialize I2C bus and MCP23017.'''
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        mcp = MCP23017(i2c)
        return mcp
    except Exception as e:
        print(f'Error initializing hardware: {e}')
        sys.exit(1)


def get_pin(mcp, relay_name):
    '''Get a pin object for the specified relay.'''
    if relay_name not in PIN_MAP:
        print(f'Error: Unknown relay "{relay_name}"')
        print(f'Valid relays: {", ".join(PIN_MAP.keys())}')
        sys.exit(1)
    
    pin = mcp.get_pin(PIN_MAP[relay_name])
    pin.direction = Direction.OUTPUT
    return pin


def get_all_pins(mcp):
    '''Get all relay pins as a dictionary.'''
    pins = {}
    for name, pin_num in PIN_MAP.items():
        pin = mcp.get_pin(pin_num)
        pin.direction = Direction.OUTPUT
        pins[name] = pin
    return pins


def show_status(mcp):
    '''Display current state of all relays.'''
    pins = get_all_pins(mcp)
    print('\nRelay Status:')
    print('-' * 25)
    for name, pin in pins.items():
        state = 'ON' if pin.value else 'OFF'
        print(f'  {name:10} : {state}')
    print('-' * 25)


def toggle_relay(mcp, relay_name, explicit_state=None):
    '''Toggle a relay or set to explicit state.'''
    pin = get_pin(mcp, relay_name)
    old_state = pin.value
    
    if explicit_state is not None:
        new_state = explicit_state
    else:
        new_state = not old_state
    
    pin.value = new_state
    
    old_str = 'ON' if old_state else 'OFF'
    new_str = 'ON' if new_state else 'OFF'
    
    if old_state == new_state:
        print(f'{relay_name}: Already {new_str}')
    else:
        print(f'{relay_name}: {old_str} -> {new_str}')


def set_mode(mcp, mode_name):
    '''Set all relays to a predefined mode configuration.'''
    if mode_name not in MODE_CONFIG:
        print(f'Error: Unknown mode "{mode_name}"')
        print(f'Valid modes: {", ".join(MODE_CONFIG.keys())}')
        sys.exit(1)
    
    config = MODE_CONFIG[mode_name]
    pins = get_all_pins(mcp)
    
    print(f'\nSetting mode: {mode_name.upper()}')
    print('-' * 25)
    
    for relay_name, target_state in config.items():
        pin = pins[relay_name]
        old_state = pin.value
        pin.value = target_state
        
        old_str = 'ON' if old_state else 'OFF'
        new_str = 'ON' if target_state else 'OFF'
        
        if old_state == target_state:
            print(f'  {relay_name:10} : {new_str} (unchanged)')
        else:
            print(f'  {relay_name:10} : {old_str} -> {new_str}')
    
    print('-' * 25)


def reset_all_relays(mcp):
    '''Turn all relays OFF.'''
    pins = get_all_pins(mcp)
    
    print('\nResetting all relays to OFF')
    print('-' * 25)
    
    for relay_name, pin in pins.items():
        old_state = pin.value
        pin.value = False
        
        old_str = 'ON' if old_state else 'OFF'
        
        if old_state:
            print(f'  {relay_name:10} : {old_str} -> OFF')
        else:
            print(f'  {relay_name:10} : OFF (unchanged)')
    
    print('-' * 25)


def apply_mode_silent(mcp, mode_name, pins=None):
    '''Apply a mode configuration without verbose output.'''
    if pins is None:
        pins = get_all_pins(mcp)
    
    config = MODE_CONFIG[mode_name]
    for relay_name, target_state in config.items():
        pins[relay_name].value = target_state


def run_cycle(mcp, timing, cycle_name='Cycle'):
    '''Execute a full run cycle with the specified timing.'''
    pins = get_all_pins(mcp)
    
    run_time = timing['run_time']
    purge_time = timing['purge_time']
    burp_time = timing['burp_time']
    rest_time = timing['rest_time']
    final_rest = timing['final_rest']
    
    # Calculate total time
    total_time = run_time + rest_time + (6 * (purge_time + burp_time)) + final_rest
    total_min = total_time // 60
    total_sec = total_time % 60
    
    print(f'\n{"="*50}')
    print(f'{cycle_name} - Total time: {total_min}m {total_sec}s')
    print(f'{"="*50}')
    
    try:
        # Step 1: Run mode
        print(f'\n[1/9] RUN mode ({run_time}s)...')
        apply_mode_silent(mcp, 'run', pins)
        for i in range(run_time):
            print(f'  {run_time - i}s remaining...', end='\r')
            time.sleep(1)
        print(f'  RUN complete.          ')
        
        # Step 2: Rest
        print(f'\n[2/9] REST ({rest_time}s)...')
        apply_mode_silent(mcp, 'rest', pins)
        time.sleep(rest_time)
        print(f'  REST complete.')
        
        # Steps 3-8: 6x Purge/Burp pairs
        for cycle_num in range(1, 7):
            step_num = 2 + cycle_num
            
            # Purge
            print(f'\n[{step_num}/9] PURGE {cycle_num}/6 ({purge_time}s)...')
            apply_mode_silent(mcp, 'purge', pins)
            for i in range(purge_time):
                print(f'  {purge_time - i}s remaining...', end='\r')
                time.sleep(1)
            print(f'  PURGE {cycle_num}/6 complete.          ')
            
            # Burp
            print(f'        BURP {cycle_num}/6 ({burp_time}s)...')
            apply_mode_silent(mcp, 'burp', pins)
            time.sleep(burp_time)
            print(f'  BURP {cycle_num}/6 complete.')
        
        # Step 9: Final rest
        print(f'\n[9/9] FINAL REST ({final_rest}s)...')
        apply_mode_silent(mcp, 'rest', pins)
        for i in range(final_rest):
            print(f'  {final_rest - i}s remaining...', end='\r')
            time.sleep(1)
        print(f'  FINAL REST complete.          ')
        
        print(f'\n{"="*50}')
        print(f'{cycle_name} COMPLETE!')
        print(f'{"="*50}\n')
        
    except KeyboardInterrupt:
        print('\n\nCycle interrupted! Setting to REST mode...')
        apply_mode_silent(mcp, 'rest', pins)
        print('All relays OFF.')
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Toggle individual relays by name or set predefined modes.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python test_relay.py -v1          Toggle v1 relay
  python test_relay.py -motor       Toggle motor relay
  python test_relay.py --status     Show all relay states
  python test_relay.py -v1 --on     Turn v1 ON
  python test_relay.py -v1 --off    Turn v1 OFF
  python test_relay.py -run         Set run mode (motor, v1, v5 ON)
  python test_relay.py -purge       Set purge mode (motor, v2 ON)
  python test_relay.py --reset      Turn all relays OFF
  python test_relay.py --cycle      Run standard cycle (~7m 47s)
  python test_relay.py --quick-cycle Run quick test cycle (~1m 29s)
        '''
    )
    
    # Full cycle options (mutually exclusive)
    cycle_group = parser.add_mutually_exclusive_group()
    cycle_group.add_argument('--cycle', '-c', action='store_true',
                             help='Run standard cycle (~7m 47s): run + 6x purge/burp + rest')
    cycle_group.add_argument('--quick-cycle', '-q', action='store_true',
                             help='Run quick test cycle (~1m 29s): run + 6x purge/burp + rest')
    
    # Mode selection flags (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-run', action='store_true', help='Set run mode (motor, v1, v5 ON)')
    mode_group.add_argument('-rest', action='store_true', help='Set rest mode (all OFF)')
    mode_group.add_argument('-purge', action='store_true', help='Set purge mode (motor, v2 ON)')
    mode_group.add_argument('-burp', action='store_true', help='Set burp mode (v5 ON)')
    mode_group.add_argument('-bleed', action='store_true', help='Set bleed mode (v2, v5 ON)')
    mode_group.add_argument('-leak', action='store_true', help='Set leak mode (v1, v2, v5 ON)')
    
    # Reset option
    parser.add_argument('--reset', '-r', action='store_true', help='Turn all relays OFF')
    
    # Relay selection flags
    parser.add_argument('-motor', action='store_true', help='Toggle motor relay')
    parser.add_argument('-v1', action='store_true', help='Toggle v1 relay')
    parser.add_argument('-v2', action='store_true', help='Toggle v2 relay')
    parser.add_argument('-v5', action='store_true', help='Toggle v5 relay')
    parser.add_argument('-shutdown', action='store_true', help='Toggle shutdown relay')
    
    # Status flag
    parser.add_argument('--status', '-s', action='store_true', help='Show current state of all relays')
    
    # Explicit state flags
    state_group = parser.add_mutually_exclusive_group()
    state_group.add_argument('--on', action='store_true', help='Explicitly turn relay ON')
    state_group.add_argument('--off', action='store_true', help='Explicitly turn relay OFF')
    
    args = parser.parse_args()
    
    # Determine explicit state if specified
    explicit_state = None
    if args.on:
        explicit_state = True
    elif args.off:
        explicit_state = False
    
    # Check which mode was selected
    selected_mode = None
    if args.run:
        selected_mode = 'run'
    elif args.rest:
        selected_mode = 'rest'
    elif args.purge:
        selected_mode = 'purge'
    elif args.burp:
        selected_mode = 'burp'
    elif args.bleed:
        selected_mode = 'bleed'
    elif args.leak:
        selected_mode = 'leak'
    
    # Check which relays were selected
    selected_relays = []
    if args.motor:
        selected_relays.append('motor')
    if args.v1:
        selected_relays.append('v1')
    if args.v2:
        selected_relays.append('v2')
    if args.v5:
        selected_relays.append('v5')
    if args.shutdown:
        selected_relays.append('shutdown')
    
    # Validate arguments
    has_cycle = args.cycle or args.quick_cycle
    if not args.status and not args.reset and not has_cycle and not selected_mode and not selected_relays:
        parser.print_help()
        sys.exit(1)
    
    # Initialize hardware
    mcp = init_hardware()
    
    # Handle cycle options first (they run full sequences)
    if args.cycle:
        run_cycle(mcp, STANDARD_TIMING, 'Standard Cycle')
        if args.status:
            show_status(mcp)
        return
    
    if args.quick_cycle:
        run_cycle(mcp, QUICK_TIMING, 'Quick Test Cycle')
        if args.status:
            show_status(mcp)
        return
    
    # Handle reset option
    if args.reset:
        reset_all_relays(mcp)
        if args.status:
            show_status(mcp)
        return
    
    # Handle mode selection
    if selected_mode:
        set_mode(mcp, selected_mode)
        if args.status:
            show_status(mcp)
        return
    
    # Show status if requested
    if args.status:
        show_status(mcp)
        if not selected_relays:
            return
    
    # Toggle selected relays
    for relay in selected_relays:
        toggle_relay(mcp, relay, explicit_state)


if __name__ == '__main__':
    main()
