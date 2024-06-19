'''
Database Manager
----------------
This module is used to manage the application's SQLite3 database.
'''

# Standard imports.
import os
from typing import Any, Dict, Optional, Tuple, Union
import sqlite3

# Local imports.
from .logger import Logger


class DatabaseManager:
    ''' 
    Database Manager:
    - Class to handle the database connections.
    '''

    _dir: str = os.path.dirname(__file__)
    _logger: Logger = Logger(__name__)

    def __init__(self, db_name: str ='app.db', table_name: str ='gm'):
        self.log = self._logger.log_message
        self.conn: Optional[sqlite3.Connection] = None
        self.db_name: str = db_name
        self.table_name: str = table_name
        if not os.path.exists(os.path.join(self._dir, 'data', 'db')):
            os.makedirs(os.path.join(self._dir, 'data', 'db'))
        self.db_path: str = os.path.join('data', 'db', self.db_name)
        self.create_table_if_not_exists()

    @classmethod
    def user(cls) -> 'DatabaseManager':
        ''' Create the user database. '''
        return cls(table_name='user')

    @classmethod
    def gm(cls) -> 'DatabaseManager':
        ''' Create the gm database. '''
        return cls(table_name='gm')

    @classmethod
    def access(cls) -> 'DatabaseManager':
        ''' Create the access database. '''
        return cls(table_name='access')

    @classmethod
    def translations(cls) -> 'DatabaseManager':
        ''' Create the translations database. '''
        return cls(db_name='translations.db', table_name='translations')

    def __enter__(self) -> sqlite3.Cursor:
        self.conn = self.create_connection()
        return self.conn.cursor()

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close_connection(exc_type, exc_value, traceback)

    def create_connection(self) -> sqlite3.Connection:
        ''' Create a connection to the database. '''
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.DatabaseError as e:
            self.log('error', f'Error connecting to database: {e}')
            raise

    def close_connection(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        ''' Close the connection to the database. '''
        if self.conn:
            if exc_type or exc_value or traceback:
                self.conn.rollback()
                self.log('error', f'Exception occured: {exc_value}')
            else:
                self.conn.commit()
            try:
                self.conn.close()
            except sqlite3.DatabaseError as e:
                self.log('error', f'Error closing database connection: {e}')

    def execute_query(self, query: str, params: Tuple =(), fetchall: bool =False, default_value: Any =None) -> Union[Dict, Any]:
        ''' Execute a query on the database. '''
        try:
            with self as cursor:
                cursor.execute(query, params)
                if fetchall:
                    results = cursor.fetchall()
                    return dict(results) if results else default_value
                result = cursor.fetchone()
                return result[0] if result else default_value
        except sqlite3.DatabaseError as e:
            self.log('error', f'Error executing query: {e}')
            raise

    def create_table_if_not_exists(self) -> None:
        ''' Create the table if it does not exist. '''
        self.execute_query(
            f'''CREATE TABLE IF NOT EXISTS {self.table_name} 
            (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT);'''
        )

    def add_setting(self, key: str, value: str) -> None:
        ''' Add a setting to the database. '''
        self.execute_query(
            f'INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?);',
            (key, value)
        )

    def remove_setting(self, key: str) -> None:
        ''' Remove a setting from the database. '''
        self.execute_query(
            f'DELETE FROM {self.table_name} WHERE key = ?;',
            (key,)
        )

    def get_setting(self, key: str, default_value: Any =None) -> Any:
        ''' Get a setting from the database. '''
        result = self.execute_query(
            f'SELECT value FROM {self.table_name} WHERE key = ?;',
            (key,)
        )
        if result is None:
            result = default_value
            self.add_setting(key, result)
        print(f'Key: {key}, Value: {result}')
        return result

    def get_all_settings(self, default_value: Any =None) -> Union[Dict, Any]:
        ''' Get all settings from the database. '''
        results = self.execute_query(
            f'SELECT key, value FROM {self.table_name};',
            fetchall=True
        )
        return results if results else default_value

    def add_translation(self, language: str, key: str, value: str) -> None:
        ''' Add a translation to the database. '''
        self.execute_query(
            f'INSERT OR REPLACE INTO {self.table_name} (language, key, value) VALUES (?, ?, ?);',
            (language, key, value)
        )

    def remove_translation(self, language: str, key: str) -> None:
        ''' Remove a translation from the database. '''
        self.execute_query(
            f'DELETE FROM {self.table_name} WHERE language = ? AND key = ?;',
            (language, key,)
        )

    def translate(self, language: str, key: str, default_value: Any =None) -> Any:
        ''' Get a translation from the database. '''
        result = self.execute_query(
            f'SELECT value FROM {self.table_name} WHERE language = ? AND key = ?;',
            (language, key,)
        )
        return result if result else default_value

    def load_translations(self, language: str, default_value: Any =None) -> Union[Dict, Any]:
        ''' Get all translations for a language from the database. '''
        results = self.execute_query(
            f'SELECT key, value FROM {self.table_name} WHERE language = ?;',
            (language,),
            fetchall=True
        )
        return results if results else default_value