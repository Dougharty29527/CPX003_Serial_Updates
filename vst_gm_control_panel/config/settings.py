'''
Direct TOML configuration access for VST Green Machine Control Panel.
'''

import os
import tomli

def load_toml(filename, directory='config'):
    '''Load a TOML file and return the parsed dictionary.'''
    path = os.path.join(directory, filename)
    try:
        with open(path, 'rb') as f:
            return tomli.load(f)
    except Exception as e:
        print(f'Error loading {path}: {e}')
        return {}

def apply_kivy_config():
    '''Apply Kivy configuration from the TOML settings.'''
    from kivy.config import Config
    
    # Initialize default sections
    default_sections = ['kivy', 'graphics', 'input', 'postproc', 'widgets', 'modules', 'network', 'log']
    for section in default_sections:
        if not Config.has_section(section):
            Config.add_section(section)
            
    # Apply our custom settings
    for section, options in app_config.get('kv', {}).items():
        if not Config.has_section(section):
            Config.add_section(section)
        for key, value in options.items():
            Config.set(section, key, str(value))
    
    Config.write()

# Load application configuration and info at runtime
app_config = load_toml('app_config.toml')
app_info = load_toml('app_info.toml')
apply_kivy_config()

# Set runtime directory (needed for system components)
if 'XDG_RUNTIME_DIR' not in os.environ:
    os.environ['XDG_RUNTIME_DIR'] = f'/run/user/{os.getuid()}'
