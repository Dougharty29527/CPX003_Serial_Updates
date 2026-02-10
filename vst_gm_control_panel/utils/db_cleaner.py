'''
Database cleaner module for managing database size.
'''

from datetime import datetime
from kivy.logger import Logger


class DatabaseCleaner:
    '''
    Handles cleanup of database tables to prevent excessive growth.
    '''
    
    def __init__(self, db_manager, table_name=None, config=None, max_records=None):
        '''
        Initialize the database cleaner.
        '''
        self.db_manager = db_manager
        self.table_name = table_name or db_manager.table_name
        # Set defaults from config or use hardcoded defaults
        self.max_records = max_records or 1000
        
        if config and 'data_management' in config:
            # First check db_cleanup section if it exists
            if 'db_cleanup' in config['data_management']:
                db_cleanup = config['data_management']['db_cleanup']
                # Look for a table-specific configuration
                if self.table_name in db_cleanup:
                    self.max_records = db_cleanup[self.table_name].get('max_records', self.max_records)
            else:
                # Fall back to old config format
                data_config = config['data_management']
                self.max_records = data_config.get('notifications_max_records', self.max_records)
    
    def cleanup_table(self):
        '''
        Remove old records from the database table to maintain max_records limit.
        '''
        try:
            # Get the current count
            count_query = f"SELECT COUNT(*) FROM {self.table_name};"
            total_records = self.db_manager.execute_query(count_query)
            
            if total_records is None:
                return 0  # No data or error
            
            if total_records is None or total_records <= self.max_records:
                return 0  # No cleanup needed
            
            # Number of records to delete
            to_delete = total_records - self.max_records
            
            # Delete oldest records based on datetime column
            # Assuming the table has an 'id' column and a 'datetime' column for sorting
            delete_query = f"""
                DELETE FROM {self.table_name}
                WHERE id IN (
                    SELECT id FROM {self.table_name}
                    ORDER BY datetime ASC
                    LIMIT {to_delete}
                );
            """
            
            # Execute the delete query
            self.db_manager.execute_query(delete_query)
            
            # Optionally run VACUUM to reclaim disk space
            self.db_manager.execute_query("VACUUM;")
            
            return to_delete
        except Exception as e:
            Logger.error(f"Error cleaning database: {e}")
            import traceback
            Logger.error(traceback.format_exc())  # Log full stack trace for better debugging
            
            # Debug info
            Logger.debug("DB DEBUG INFO:")
            Logger.debug(f"  Table: {self.table_name}")
            Logger.debug(f"  Max records: {self.max_records}")
            
            # Try to get table schema
            try:
                schema_query = f"PRAGMA table_info({self.table_name});"
                schema = self.db_manager.execute_query(schema_query, fetchall=True)
                Logger.debug(f"  Table schema: {schema}")
            except Exception as schema_error:
                Logger.error(f"  Error getting schema: {schema_error}")
                
            return 0
