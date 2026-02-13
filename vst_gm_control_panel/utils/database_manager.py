"""
Database Manager Module

This module provides robust database management for the VST Green Machine Control Panel.
It handles database connections, query execution, and transaction management with
proper error handling and concurrency support.
"""

# Standard imports
from datetime import datetime
import logging
import os
import queue
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union

# Kivy imports
from kivymd.app import MDApp

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database Manager for handling SQLite database connections and operations.
    
    This class provides methods for database interaction with robust error handling,
    connection management, and operation queuing to prevent concurrency issues.
    All database operations are thread-safe using thread-local connections.
    """
    # Class-level variables for operation queue
    _operation_queue = queue.Queue()
    _worker_thread = None
    _worker_running = False
    _queue_lock = threading.Lock()
    
    # Thread-local storage for connections
    _local = threading.local()
    
    # Tracking all active managers for cleanup
    _all_managers = set()
    _managers_lock = threading.Lock()

    def __init__(self, db_name='app.db', table_name='gm'):
        """
        Initialize a database manager instance.
        
        Args:
            db_name: Name of the database file
            table_name: Name of the table to use for operations
        """
        self.app = MDApp.get_running_app()
        self.db_name = db_name
        self.table_name = table_name
        
        # Use absolute path to ensure consistent database location
        # Base directory is always /home/cpx003/vst_gm_control_panel/vst_gm_control_panel/data/db
        vst_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        self.base_dir = os.path.join(vst_root, 'data', 'db')
        
        # Ensure the directory exists
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
        # Set absolute path for the database
        self.db_path = os.path.join(self.base_dir, self.db_name)
        
        # Register this manager instance for cleanup
        with self._managers_lock:
            self._all_managers.add(self)
        
        self.create_table_if_not_exists()

    @classmethod
    def from_table(cls, table_name, db_name='app.db'):
        """
        Create a database manager from a db and/or table name.
        
        Args:
            table_name: Name of the table to use
            db_name: Name of the database file
            
        Returns:
            A new DatabaseManager instance
        """
        return cls(db_name=db_name, table_name=table_name)

    def get_thread_connection(self):
        """
        Get a database connection for the current thread.
        
        This method ensures each thread has its own connection to maintain
        SQLite's thread affinity requirements. Connections are cached in
        thread-local storage for reuse.
        
        Returns:
            A SQLite connection object specific to the current thread
        """
        # Get unique thread identifier
        thread_id = threading.get_ident()
        
        # Create thread-local storage attribute if it doesn't exist
        if not hasattr(self._local, 'connections'):
            self._local.connections = {}
        
        # Create connection key that's truly unique per thread AND database
        conn_key = f"{self.db_path}:{thread_id}"
        
        # Create new connection if none exists for this thread
        if conn_key not in self._local.connections or self._local.connections[conn_key] is None:
            try:
                # Create connection with proper SQLite settings
                connection = sqlite3.connect(
                    self.db_path,
                    isolation_level=None,  # Autocommit mode
                    check_same_thread=False,  # Allow thread transfer (we manage it properly)
                    timeout=30.0  # Prevent indefinite blocking
                )
                connection.row_factory = sqlite3.Row
                
                # Test the connection immediately
                connection.execute("SELECT 1")
                
                # Store in thread-local storage
                self._local.connections[conn_key] = connection
                logger.debug(f"Created new thread-local connection for thread {thread_id}")
                
            except sqlite3.DatabaseError as e:
                logger.error(f"Error creating database connection: {e}")
                raise
        
        # Validate existing connection is still alive
        try:
            self._local.connections[conn_key].execute("SELECT 1")
            return self._local.connections[conn_key]
        except sqlite3.Error:
            # Connection is dead, recreate it
            logger.warning(f"Recreating dead connection for thread {thread_id}")
            try:
                connection = sqlite3.connect(
                    self.db_path,
                    isolation_level=None,
                    check_same_thread=False,
                    timeout=30.0
                )
                connection.row_factory = sqlite3.Row
                connection.execute("SELECT 1")  # Test immediately
                self._local.connections[conn_key] = connection
                return connection
            except sqlite3.DatabaseError as e:
                logger.error(f"Failed to recreate connection: {e}")
                raise

    def __enter__(self):
        """
        Context manager entry method - get cursor for thread-local connection.
        
        Returns:
            SQLite cursor for the current thread's connection
        """
        # Get connection for this thread
        conn = self.get_thread_connection()
        
        # Return cursor from the connection
        return conn.cursor()

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager exit method.
        
        This handles transaction management (commit/rollback) but does not
        close the connection, as it may be reused by the same thread.
        
        Args:
            exc_type: Exception type, if any
            exc_value: Exception value, if any
            traceback: Traceback, if any
        """
        conn = self.get_thread_connection()
        
        # Handle transaction
        if exc_type or exc_value or traceback:
            conn.rollback()
        else:
            conn.commit()

    def create_connection(self):
        """
        Create a connection to the database.
        
        This method is maintained for backward compatibility but
        now uses thread-local connections internally.
        
        Returns:
            A SQLite connection object
        """
        return self.get_thread_connection()

    def close_connection(self, exc_type, exc_value, traceback):
        """
        Handle transaction management but keep connection open.
        
        This method is maintained for backward compatibility but
        no longer actually closes connections, as they are now
        managed in thread-local storage.
        
        Args:
            exc_type: Exception type, if any
            exc_value: Exception value, if any
            traceback: Traceback, if any
        """
        conn = self.get_thread_connection()
        
        # Handle transaction
        if exc_type or exc_value or traceback:
            conn.rollback()
        else:
            conn.commit()

    @classmethod
    def close_thread_connections(cls):
        """
        Close all connections for the current thread.
        
        This should be called when a thread is finishing to clean up
        resources and prevent connection leaks.
        """
        if hasattr(cls._local, 'connections'):
            thread_id = threading.get_ident()
            for conn_key, conn in cls._local.connections.items():
                if conn_key.endswith(f":{thread_id}"):
                    try:
                        conn.close()
                        logger.debug(f"Closed thread-local connection for {conn_key}")
                    except Exception as e:
                        logger.error(f"Error closing connection {conn_key}: {e}")
            
            # Remove connections for this thread
            cls._local.connections = {k: v for k, v in cls._local.connections.items() 
                                     if not k.endswith(f":{thread_id}")}

    @classmethod
    def close_all_connections(cls):
        """
        Close all connections across all threads.
        
        This should be called during application shutdown to ensure
        all database connections are properly closed.
        """
        if hasattr(cls._local, 'connections'):
            for conn_key, conn in cls._local.connections.items():
                try:
                    conn.close()
                    logger.debug(f"Closed connection {conn_key}")
                except Exception as e:
                    logger.error(f"Error closing connection {conn_key}: {e}")
            
            # Clear all connections
            cls._local.connections = {}

    def execute_query(
        self,
        query,
        params=(),
        fetchall=False,
        default_value=None,
    ):
        """
        Execute a query on the database using thread-local connections.
        
        Args:
            query: The SQL query to execute
            params: Parameters for the query
            fetchall: Whether to fetch all results
            default_value: Default value if no results found
            
        Returns:
            Query results based on fetchall parameter
        """
        try:
            with self as cursor:
                cursor.execute(query, params)
                if fetchall:
                    results = cursor.fetchall()
                    if results and len(results[0]) == 1:
                        return [result[0] for result in results] if results else default_value
                    return dict(results) if results else default_value
                result = cursor.fetchone()
                return result[0] if result else default_value
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error executing query: {e}")
            raise

    def create_table_if_not_exists(self):
        '''
        Create the table if it does not exist.
        '''
        if 'notifications' in self.db_name:
            self.execute_query(
            f'''CREATE TABLE IF NOT EXISTS {self.table_name}
            (id INTEGER PRIMARY KEY, datetime TEXT, notification TEXT);'''
            )
        else:
            self.execute_query(
                f'''CREATE TABLE IF NOT EXISTS {self.table_name}
                (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT);'''
            )

    def add_setting(self, key, value):
        '''
        Purpose:
        - Add a setting to the database.
        Parameters:
        - key: The key for the setting (str).
        - value: The value for the setting (str).
        '''
        self.execute_query(
            f'INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?);',
            (key, value)
        )

    def remove_setting(self, key):
        '''
        Purpose:
        - Remove a setting from the database.
        Parameters:
        - key: The key for the setting (str).
        '''
        self.execute_query(
            f'DELETE FROM {self.table_name} WHERE key = ?;',
            (key,)
        )

    def get_setting(self, key, default_value=None):
        '''
        Purpose:
        - Get a setting from the database.
        Parameters:
        - key: The key for the setting (str).
        - default_value: The default value to return if no results are found (Any).
        Returns:
        - Any: The value of the setting.
        '''
        result = self.execute_query(
            f'SELECT value FROM {self.table_name} WHERE key = ?;',
            (key,)
        )
        if result is None:
            result = default_value
            self.add_setting(key, result)
        return result

    def get_all_settings(self, default_value=None):
        '''
        Purpose:
        - Get all settings from the database.
        Parameters:
        - default_value: The default value to return if no results are found (Any).
        Returns:
        - Dict or Any: The results of the query.
        '''
        results = self.execute_query(
            f'SELECT key, value FROM {self.table_name};',
            fetchall=True
        )
        return results if results else default_value

    def get_permissions(self, value):
        '''
        Find a value in the database.
        '''
        return self.execute_query(
            f'SELECT level, screen, access FROM {self.table_name} WHERE level = ?;',
            (value,),
        )

    def check_permissions(self, value):
        '''
        Check passphrase in the database.
        Returns the level associated with the password.
        '''
        try:
            # Get the level for this password by checking the access column
            level = self.execute_query(
                f'SELECT level FROM {self.table_name} WHERE access = ?;',
                (str(value),)  # Ensure value is converted to string for comparison
            )
            
            # If no level found, return None
            if not level:
                return None
                
            # Return the level as a string
            return str(level)
            
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            return None

    def add_translation(self, language, key, value):
        '''
        Purpose:
        - Add a translation to the database.
        Parameters:
        - language: The language for the translation (str).
        - key: The key for the translation (str).
        - value: The value for the translation (str).
        '''
        self.execute_query(
            f'INSERT OR REPLACE INTO {self.table_name} (language, key, value) VALUES (?, ?, ?);',
            (language, key, value)
        )

    def remove_translation(self, language, key):
        '''
        Purpose:
        - Remove a translation from the database.
        Parameters:
        - language: The language for the translation (str).
        - key: The key for the translation (str).
        '''
        self.execute_query(
            f'DELETE FROM {self.table_name} WHERE language = ? AND key = ?;',
            (language, key,)
        )

    def translate(self, language, key, default_value=None):
        '''
        Purpose:
        - Translate a key.
        Parameters:
        - language: The language for the translation (str).
        - key: The key for the translation (str).
        - default_value: The default value to return if no results are found (Any).
        Returns:
        - Any: The value of the translation.
        '''
        result = self.execute_query(
            f'SELECT value FROM {self.table_name} WHERE language = ? AND key = ?;',
            (language, key,)
        )
        return result if result else default_value

    def load_translations(self, language, default_value=None):
        '''
        Purpose:
        - Load all translations for a language.
        Parameters:
        - language: The language for the translations (str).
        - default_value: The default value to return if no results are found (Any).
        Returns:
        - Dict or Any: The results of the query.
        '''
        results = self.execute_query(
            f'SELECT key, value FROM {self.table_name} WHERE language = ?;',
            (language,),
            fetchall=True
        )
        return results if results else default_value

    def add_notification(self, datetime, notification):
        """
        Add a notification to the database.
        
        Args:
            datetime: Timestamp for the notification
            notification: The notification text to store
        """
        self.execute_query(
            f'INSERT INTO {self.table_name} (datetime, notification) VALUES (?, ?);',
            (datetime, notification)
        )
        
    # Queue-based operation methods
    
    @classmethod
    def initialize_worker(cls):
        """
        Start the background worker thread if not already running.
        
        This method starts a daemon thread that processes database operations
        from the queue, which helps prevent database contention issues.
        """
        with cls._queue_lock:
            if cls._worker_thread is None or not cls._worker_thread.is_alive():
                cls._worker_running = True
                cls._worker_thread = threading.Thread(
                    target=cls._process_queue,
                    daemon=True,
                    name="DatabaseWorker"
                )
                cls._worker_thread.start()
                logger.info("Database worker thread started")
    
    @classmethod
    def _process_queue(cls):
        """
        Process operations from the queue in background thread.
        
        This method runs in a separate thread and processes database operations
        sequentially to prevent concurrency issues. Each operation gets its own
        database connection to ensure thread safety.
        """
        while cls._worker_running:
            try:
                # Get operation with 1-second timeout to allow checking _worker_running
                operation, args, kwargs, callback = cls._operation_queue.get(timeout=1.0)
                
                try:
                    # Extract operation info
                    operation_name = operation.__name__
                    logger.debug(f"Processing queued operation: {operation_name}")
                    
                    # Execute the operation with thread-local handling
                    result = cls._execute_in_worker_thread(operation, *args, **kwargs)
                    
                    # Call the callback with the result if provided
                    if callback:
                        callback(result)
                        
                    logger.debug(f"Completed queued operation: {operation_name}")
                except Exception as e:
                    # Log error but continue processing queue
                    logger.error(f"Error processing queued operation: {e}")
                finally:
                    # Mark task as done even if it failed
                    cls._operation_queue.task_done()
                    
            except queue.Empty:
                # Normal timeout, just continue
                pass
    
    @classmethod
    def _execute_in_worker_thread(cls, operation, *args, **kwargs):
        """
        Execute an operation with thread-local database connections.
        
        This method ensures SQLite's thread affinity rules are respected
        by creating connections specific to the worker thread.
        
        Args:
            operation: Function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
        """
        # Check if this is a DatabaseManager method that needs special handling
        if hasattr(operation, '__self__') and isinstance(operation.__self__, DatabaseManager):
            # Get the instance and method name
            instance = operation.__self__
            method_name = operation.__name__
            
            # Create a new database manager instance for this thread with the same parameters
            thread_db = DatabaseManager(
                db_name=instance.db_name, 
                table_name=instance.table_name
            )
            
            # Get the corresponding method on the thread-local instance
            thread_method = getattr(thread_db, method_name)
            
            # Execute the method with the provided arguments
            return thread_method(*args, **kwargs)
        
        # For standalone functions or static methods, just execute them
        return operation(*args, **kwargs)
    
    @classmethod
    def queue_operation(cls, operation, *args, callback=None, **kwargs):
        """
        Queue a database operation to be executed on the worker thread.
        
        This method is the primary way to safely execute database operations
        in response to signals or other asynchronous events.
        
        Args:
            operation: The function to execute
            *args: Arguments to pass to the operation
            callback: Optional function to call with the result
            **kwargs: Keyword arguments to pass to the operation
        """
        # Ensure worker is running
        cls.initialize_worker()
        
        # Add operation to queue
        cls._operation_queue.put((operation, args, kwargs, callback))
        logger.debug(f"Operation {operation.__name__} queued")
    
    @classmethod
    def execute_with_retry(cls, operation, max_retries=3, retry_delay=0.5):
        """
        Execute a database operation with retry logic.
        
        This method attempts to execute a database operation and retries
        on transient errors like database locks.
        
        Args:
            operation: Function to execute
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (increases with each attempt)
            
        Returns:
            The result of the operation
            
        Raises:
            sqlite3.Error: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return operation()
            except sqlite3.OperationalError as e:
                last_error = e
                
                # Check if this is a retriable error
                error_msg = str(e).lower()
                if ("database is locked" in error_msg or 
                    "database disk image is malformed" in error_msg):
                    
                    # Use exponential backoff for retries
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Database error (attempt {attempt+1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                    continue
                    
                # Non-retriable operational error
                raise
            except Exception as e:
                # Non-sqlite operational error
                logger.error(f"Database operation failed: {e}")
                raise
        
        # If we've exhausted retries, raise the last error
        if last_error:
            logger.error(f"Database operation failed after {max_retries} attempts: {last_error}")
            raise last_error
