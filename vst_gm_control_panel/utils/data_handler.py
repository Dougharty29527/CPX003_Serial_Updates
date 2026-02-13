"""
Data Handler for VST GM Control Panel

Handles data persistence, calibration storage, and backfill data management
for the ESP32 IO Board integration.
"""

import logging
import json
import os
from datetime import datetime

class DataHandler:
    """
    Data handler for managing ESP32 sensor data, calibration, and backfill operations.
    """

    def __init__(self, app=None):
        """
        Initialize the data handler.

        Args:
            app: Kivy app instance for accessing application data
        """
        self.app = app
        self.logger = logging.getLogger(__name__)

        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)

        # Backfill data storage
        self.backfill_file = os.path.join(self.data_dir, 'backfill_data.json')

    def save_calibration(self, calibration_value):
        """
        Save pressure sensor calibration value.

        Args:
            calibration_value (float): ADC zero point calibration value

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            cal_file = os.path.join(self.data_dir, 'pressure_calibration.json')

            cal_data = {
                'adc_zero_point': calibration_value,
                'timestamp': datetime.now().isoformat(),
                'source': 'esp32'
            }

            with open(cal_file, 'w') as f:
                json.dump(cal_data, f, indent=2)

            self.logger.info(f"Saved ESP32 calibration: {calibration_value}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save calibration: {e}")
            return False

    def save_backfill_data(self, backfill_records):
        """
        Save backfill data received from ESP32 after passthrough mode.

        Args:
            backfill_records (list): List of backfill data records with timestamps

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Load existing backfill data if any
            existing_data = []
            if os.path.exists(self.backfill_file):
                try:
                    with open(self.backfill_file, 'r') as f:
                        existing_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_data = []

            # Add new records
            existing_data.extend(backfill_records)

            # Save updated data
            with open(self.backfill_file, 'w') as f:
                json.dump(existing_data, f, indent=2)

            self.logger.info(f"Saved {len(backfill_records)} backfill records to {self.backfill_file}")

            # TODO: Here you would typically trigger cloud synchronization
            # self._sync_to_cloud(existing_data)

            return True

        except Exception as e:
            self.logger.error(f"Failed to save backfill data: {e}")
            return False

    def get_backfill_data(self, limit=None):
        """
        Retrieve stored backfill data.

        Args:
            limit (int, optional): Maximum number of records to return

        Returns:
            list: List of backfill data records
        """
        try:
            if not os.path.exists(self.backfill_file):
                return []

            with open(self.backfill_file, 'r') as f:
                data = json.load(f)

            if limit and isinstance(limit, int):
                return data[-limit:]  # Return most recent records

            return data

        except Exception as e:
            self.logger.error(f"Failed to read backfill data: {e}")
            return []

    def clear_backfill_data(self):
        """
        Clear all stored backfill data after successful cloud sync.

        Returns:
            bool: True if cleared successfully, False otherwise
        """
        try:
            if os.path.exists(self.backfill_file):
                # Instead of deleting, create backup
                backup_file = f"{self.backfill_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.backfill_file, backup_file)
                self.logger.info(f"Backfill data backed up to {backup_file}")

            # Create empty file
            with open(self.backfill_file, 'w') as f:
                json.dump([], f)

            return True

        except Exception as e:
            self.logger.error(f"Failed to clear backfill data: {e}")
            return False

    def get_calibration(self):
        """
        Retrieve the current pressure calibration value.

        Returns:
            dict or None: Calibration data or None if not found
        """
        try:
            cal_file = os.path.join(self.data_dir, 'pressure_calibration.json')

            if not os.path.exists(cal_file):
                return None

            with open(cal_file, 'r') as f:
                return json.load(f)

        except Exception as e:
            self.logger.error(f"Failed to read calibration: {e}")
            return None

    # Note: The actual app properties are accessed via self.app.* in the main application
    # This data_handler serves as a bridge between the modem and the main app