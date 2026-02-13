'''
Log archiver module for managing CSV log file rotation and archiving.
'''

# Standard imports
import csv
import os
import zipfile
from datetime import datetime
from pathlib import Path

# Kivy imports
from kivy.logger import Logger


class LogArchiver:
    '''
    Handles archiving of log files when they reach a specified line count.
    All archives are retained permanently.
    '''

    def __init__(self, log_path, config=None):
        '''
        Initialize the log archiver.
        '''
        self.log_path = Path(log_path)
        self.archive_dir = self.log_path.parent / 'log_archives'
        
        # Set defaults from config or use hardcoded defaults
        if config and 'data_management' in config:
            data_config = config['data_management']
            self.max_lines = data_config.get('log_max_lines', 1000)
        else:
            self.max_lines = 1000
        
        # Ensure archive directory exists
        if not self.archive_dir.exists():
            self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def count_lines(self):
        '''Count the number of lines in the log file.'''
        if not self.log_path.exists():
            return 0
            
        with self.log_path.open('r', newline='') as f:
            return sum(1 for _ in f)
    
    def archive_if_needed(self):
        '''Check if log needs archiving and archive if so.'''
        # Check if the file exists and has more than max_lines
        if not self.log_path.exists() or self.count_lines() <= self.max_lines:
            return False
            
        return self.archive_log()
    
    def archive_log(self):
        '''
        Archive the current log file and create a new one with just headers.
        All archives are retained permanently.
        '''
        try:
            # Read the log file to get first and last entry timestamps
            try:
                # Use binary mode to handle possible NUL bytes
                with self.log_path.open('rb') as f:
                    # Read first few lines manually to avoid CSV reader issues with NUL bytes
                    lines = []
                    header_line = f.readline().decode('utf-8', errors='replace').strip()
                    headers = header_line.split(',')
                    
                    # Get the first data line
                    first_line_raw = f.readline()
                    if not first_line_raw:
                        return False  # Empty file or only header
                    
                    first_line_text = first_line_raw.decode('utf-8', errors='replace').strip()
                    first_line = first_line_text.split(',')
                    
                    # Get first line timestamps from split values
                    # Date (Local) and Time (Local) are at index 6 and 7
                    first_date = first_line[6]
                    first_time = first_line[7]
                    
                    # For the last line, we'll use a safer approach
                    # Read the file in chunks from the end
                    f.seek(0, 2)  # Go to end of file
                    file_size = f.tell()
                    
                    # Read the last chunk of the file
                    chunk_size = min(10240, file_size)  # Use 10KB or file size, whichever is smaller
                    f.seek(max(0, file_size - chunk_size))
                    last_chunk = f.read(chunk_size).decode('utf-8', errors='replace')
                    
                    # Get the last line
                    last_lines = last_chunk.strip().split('\n')
                    last_line_text = last_lines[-1]
                    last_line = last_line_text.split(',')
                
                # If we can't get valid data, use datestamp
                if len(first_line) < 8 or len(last_line) < 8:
                    current_time = datetime.now()
                    first_date = last_date = current_time.strftime("%Y/%m/%d")
                    first_time = last_time = current_time.strftime("%H:%M:%S")
                else:
                    # Get the timestamps from the last line
                    last_date = last_line[6]
                    last_time = last_line[7]
            except Exception as e:
                Logger.error(f"Error reading log file: {e}")
                # Use current datetime as fallback
                current_time = datetime.now()
                first_date = last_date = current_time.strftime("%Y/%m/%d")
                first_time = last_time = current_time.strftime("%H:%M:%S")
                
            # Create a zip filename using the date/time range
            first_datetime = f"{first_date.replace('/', '')}-{first_time.split()[0].replace(':', '')}"
            last_datetime = f"{last_date.replace('/', '')}-{last_time.split()[0].replace(':', '')}"
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            zip_filename = f"logfile_{first_datetime}_to_{last_datetime}_{timestamp}.zip"
            zip_path = self.archive_dir / zip_filename
            
            # Create the zip file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(self.log_path, arcname=self.log_path.name)
            
            # Create a new log file with just headers
            with self.log_path.open('w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
            return True
        except Exception as e:
            Logger.error(f"Error archiving log file: {e}")
            import traceback
            Logger.error(traceback.format_exc())  # Log full stack trace for better debugging
            
            # Debug info
            Logger.debug("LOG DEBUG INFO:")
            Logger.debug(f"  Log path: {self.log_path} (exists: {self.log_path.exists()})")
            Logger.debug(f"  Archive dir: {self.archive_dir} (exists: {self.archive_dir.exists()})")
            if self.log_path.exists():
                Logger.debug(f"  Log line count: {self.count_lines()}")
            return False
