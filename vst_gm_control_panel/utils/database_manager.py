'''
=================================================
                Database Manager
=================================================

This module is used to manage the application's SQLite3 database.
'''

# Standard imports.
import os
import sqlite3

# Local imports.
from utils import Logger


class DatabaseManager:
    '''
    Database Manager
    ----------------
    This class is used to handle the database connections.
    '''

    _logger = Logger(__name__)
    log = _logger.log_message

    def __init__(self, db_name='app.db', table_name='gm'):
        self.conn = None
        self.db_name = db_name
        self.table_name = table_name
        self._db_directory = os.path.join('data', 'db')
        if not os.path.exists(self._db_directory):
            os.makedirs(self._db_directory)
        self.db_path = os.path.join(self._db_directory, self.db_name)
        self.create_table_if_not_exists()

    @classmethod
    def user(cls):
        ''' Create the user database. '''
        return cls(table_name='user')

    @classmethod
    def gm(cls):
        ''' Create the gm database. '''
        return cls(table_name='gm')

    @classmethod
    def access(cls):
        ''' Create the access database. '''
        return cls(table_name='access')

    @classmethod
    def translations(cls):
        ''' Create the translations database. '''
        return cls(db_name='translations.db', table_name='translations')

    def __enter__(self):
        self.conn = self.create_connection()
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection(exc_type, exc_value, traceback)

    def create_connection(self):
        ''' Create a connection to the database. '''
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.DatabaseError as e:
            self.log('error', f'Error connecting to database: {e}')
            raise

    def close_connection(self, exc_type, exc_value, traceback):
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

    def execute_query(self, query, params=(), fetchall=False, default_value=None):
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

    def create_table_if_not_exists(self):
        ''' Create the table if it does not exist. '''
        self.execute_query(
            f'''CREATE TABLE IF NOT EXISTS {self.table_name} 
            (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT);'''
        )

    def add_setting(self, key, value):
        ''' Add a setting to the database. '''
        self.execute_query(
            f'INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?);',
            (key, value)
        )

    def remove_setting(self, key):
        ''' Remove a setting from the database. '''
        self.execute_query(
            f'DELETE FROM {self.table_name} WHERE key = ?;',
            (key,)
        )

    def get_setting(self, key, default_value=None):
        ''' Get a setting from the database. '''
        result = self.execute_query(
            f'SELECT value FROM {self.table_name} WHERE key = ?;',
            (key,)
        )
        return result if result else default_value

    def get_all_settings(self, default_value=None):
        ''' Get all settings from the database. '''
        results = self.execute_query(
            f'SELECT key, value FROM {self.table_name};',
            fetchall=True
        )
        return results if results else default_value

    def add_translation(self, language, key, value):
        ''' Add a translation to the database. '''
        self.execute_query(
            f'INSERT OR REPLACE INTO {self.table_name} (language, key, value) VALUES (?, ?, ?);',
            (language, key, value)
        )

    def remove_translation(self, language, key):
        ''' Remove a translation from the database. '''
        self.execute_query(
            f'DELETE FROM {self.table_name} WHERE language = ? AND key = ?;',
            (language, key,)
        )

    def get_translation(self, language, key, default_value=None):
        ''' Get a translation from the database. '''
        result = self.execute_query(
            f'SELECT value FROM {self.table_name} WHERE language = ? AND key = ?;',
            (language, key,)
        )
        return result if result else default_value

    def load_translations(self, language, default_value=None):
        ''' Get all translations for a language from the database. '''
        results = self.execute_query(
            f'SELECT key, value FROM {self.table_name} WHERE language = ?;',
            (language,),
            fetchall=True
        )
        return results if results else default_value