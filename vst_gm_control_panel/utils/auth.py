'''
Authentication utilities for SORACOM API.
'''

# Standard imports.
import json
import requests

## Kivy imports.
from kivy.logger import Logger

# Local imports.

class AuthError(Exception):
    '''Base class for authentication errors'''
    pass

class CredentialsError(AuthError):
    '''Error when credentials are missing or invalid'''
    pass

class ApiError(AuthError):
    '''Error when API request fails'''
    pass

def get_credentials():
    from .database_manager import DatabaseManager
    try:
        # Get credentials from database
        db = DatabaseManager.from_table('auth', 'sys/auth.db')
        email = db.get_setting('soracom_email')
        password = db.get_setting('soracom_password')
        if not email or not password:
            raise CredentialsError('Email or password not found in database')
        return email, password
    except CredentialsError as e:
        Logger.error(f'Modem: {str(e)}')
        raise
    except Exception as e:
        Logger.error(f'Modem: Error getting credentials: {e}')
        raise CredentialsError(f'Failed to retrieve credentials: {str(e)}')

def get_auth():
    '''
    Get SORACOM authentication tokens.
    '''
    try:
        email, password = get_credentials()
        
        headers = {'Content-type': 'application/json'}
        data = {'email': email, 'password': password}
        
        try:
            response = requests.post('https://g.api.soracom.io/v1/auth',
                                  headers=headers,
                                  json=data,
                                  timeout=30)
        except requests.exceptions.RequestException as e:
            raise ApiError(f'Failed to connect to SORACOM API: {str(e)}')

        if response.status_code != 200:
            raise ApiError(f'Failed to authenticate: {response.status_code} {response.text}')

        data = response.json()
        api_key = data.get('apiKey')
        token = data.get('token')

        if not api_key or not token:
            raise ApiError('API key or token not found in response')

        return api_key, token

    except (CredentialsError, ApiError) as e:
        Logger.error(f'Modem: {str(e)}')
        raise
    except Exception as e:
        Logger.error(f'Modem: Unexpected error during authentication: {e}')
        raise ApiError(f'Authentication failed: {str(e)}')