#!/usr/bin/env python3
"""
Cycle State Manager for handling pause/resume functionality during GM faults.
"""

import json
import time
import threading
import multiprocessing
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from kivy.logger import Logger
from kivymd.app import MDApp


class CycleStateManager:
    """
    Manages cycle state for pause/resume functionality during GM faults.
    Handles storing and restoring cycle state across process interruptions.
    """
    
    def __init__(self):
        self.app = MDApp.get_running_app()
        self._state_lock = threading.Lock()
        self._pause_event = multiprocessing.Event()
        self._resume_event = multiprocessing.Event()
        self._current_state = None
        
    def save_cycle_state(self, sequence: List[Tuple[str, float]], current_step: int, 
                        elapsed_time: float, is_manual: bool = False) -> bool:
        """
        Save the current cycle state to database for pause/resume functionality.
        
        Args:
            sequence: The full sequence being executed
            current_step: Current step index in the sequence
            elapsed_time: Time elapsed in current step
            is_manual: Whether this is a manual mode cycle
            
        Returns:
            bool: True if state saved successfully
        """
        try:
            with self._state_lock:
                state_data = {
                    'sequence': sequence,
                    'current_step': current_step,
                    'elapsed_time': elapsed_time,
                    'is_manual': is_manual,
                    'pause_timestamp': time.time(),
                    'original_step_duration': sequence[current_step][1] if current_step < len(sequence) else 0
                }
                
                # Store in database
                self.app.gm_db.add_setting('cycle_pause_state', json.dumps(state_data))
                self.app.gm_db.add_setting('cycle_is_paused', 'true')
                
                self._current_state = state_data
                Logger.info(f'CycleStateManager: Saved cycle state - step {current_step}, elapsed {elapsed_time}s')
                return True
                
        except Exception as e:
            Logger.error(f'CycleStateManager: Error saving cycle state: {e}')
            return False
    
    def load_cycle_state(self) -> Optional[Dict[str, Any]]:
        """
        Load the saved cycle state from database.
        
        Returns:
            Dict containing cycle state or None if no saved state
        """
        try:
            with self._state_lock:
                is_paused = self.app.gm_db.get_setting('cycle_is_paused', 'false')
                if is_paused != 'true':
                    return None
                    
                state_json = self.app.gm_db.get_setting('cycle_pause_state')
                if not state_json:
                    return None
                    
                state_data = json.loads(state_json)
                self._current_state = state_data
                Logger.info(f'CycleStateManager: Loaded cycle state - step {state_data.get("current_step", 0)}')
                return state_data
                
        except Exception as e:
            Logger.error(f'CycleStateManager: Error loading cycle state: {e}')
            return None
    
    def clear_cycle_state(self):
        """Clear the saved cycle state from database."""
        try:
            with self._state_lock:
                self.app.gm_db.add_setting('cycle_pause_state', '')
                self.app.gm_db.add_setting('cycle_is_paused', 'false')
                self._current_state = None
                Logger.info('CycleStateManager: Cleared cycle state')
                
        except Exception as e:
            Logger.error(f'CycleStateManager: Error clearing cycle state: {e}')
    
    def is_cycle_paused(self) -> bool:
        """Check if a cycle is currently paused."""
        try:
            is_paused = self.app.gm_db.get_setting('cycle_is_paused', 'false')
            return is_paused == 'true'
        except Exception:
            return False
    
    def calculate_remaining_time(self, state_data: Dict[str, Any]) -> float:
        """
        Calculate remaining time for the current step based on pause duration.
        
        Args:
            state_data: The saved cycle state
            
        Returns:
            float: Remaining time for current step
        """
        try:
            original_duration = state_data.get('original_step_duration', 0)
            elapsed_time = state_data.get('elapsed_time', 0)
            remaining_time = max(0, original_duration - elapsed_time)
            
            Logger.debug(f'CycleStateManager: Original duration: {original_duration}s, '
                        f'elapsed: {elapsed_time}s, remaining: {remaining_time}s')
            return remaining_time
            
        except Exception as e:
            Logger.error(f'CycleStateManager: Error calculating remaining time: {e}')
            return 0
    
    def create_resume_sequence(self, state_data: Dict[str, Any]) -> List[Tuple[str, float]]:
        """
        Create a new sequence starting from the paused point.
        
        Args:
            state_data: The saved cycle state
            
        Returns:
            List of (mode, duration) tuples for remaining sequence
        """
        try:
            original_sequence = state_data.get('sequence', [])
            current_step = state_data.get('current_step', 0)
            
            if current_step >= len(original_sequence):
                Logger.warning('CycleStateManager: Current step beyond sequence length')
                return []
            
            # Calculate remaining time for current step
            remaining_time = self.calculate_remaining_time(state_data)
            
            # Build resume sequence
            resume_sequence = []
            
            # Add current step with remaining time if there's time left
            if remaining_time > 0:
                current_mode = original_sequence[current_step][0]
                resume_sequence.append((current_mode, remaining_time))
            
            # Add all remaining steps
            for i in range(current_step + 1, len(original_sequence)):
                resume_sequence.append(original_sequence[i])
            
            Logger.info(f'CycleStateManager: Created resume sequence with {len(resume_sequence)} steps')
            return resume_sequence
            
        except Exception as e:
            Logger.error(f'CycleStateManager: Error creating resume sequence: {e}')
            return []
    
    def pause_cycle(self, io_manager) -> bool:
        """
        Pause the currently running cycle.
        
        Args:
            io_manager: The IOManager instance
            
        Returns:
            bool: True if pause was successful
        """
        try:
            Logger.info('CycleStateManager: Initiating cycle pause for GM fault')
            Logger.debug(f'CycleStateManager: MODE CHANGE - Pausing cycle, current mode: {io_manager.mode}')
            
            # Signal the cycle to pause
            self._pause_event.set()
            
            # Stop the current cycle process
            if hasattr(io_manager, 'cycle_process') and io_manager.cycle_process:
                if io_manager.cycle_process.is_alive():
                    io_manager.stop_cycle()
                    Logger.info('CycleStateManager: Stopped cycle process for pause')
                    Logger.debug('CycleStateManager: MODE CHANGE - Cycle process terminated for pause')
            
            # Set to rest mode during pause
            io_manager.set_rest()
            Logger.debug('CycleStateManager: MODE CHANGE - Set to rest mode during pause')
            
            return True
            
        except Exception as e:
            Logger.error(f'CycleStateManager: Error pausing cycle: {e}')
            return False
    
    def resume_cycle(self, io_manager) -> bool:
        """
        Resume the paused cycle from where it left off.
        
        Args:
            io_manager: The IOManager instance
            
        Returns:
            bool: True if resume was successful
        """
        try:
            # Load the saved state
            state_data = self.load_cycle_state()
            if not state_data:
                Logger.warning('CycleStateManager: No saved state found for resume')
                return False
            
            Logger.debug(f'CycleStateManager: MODE CHANGE - Resuming from step {state_data.get("current_step", 0)} of {len(state_data.get("sequence", []))} total steps')
            
            # Create resume sequence
            resume_sequence = self.create_resume_sequence(state_data)
            if not resume_sequence:
                Logger.warning('CycleStateManager: No sequence to resume')
                self.clear_cycle_state()
                return False
            
            Logger.info(f'CycleStateManager: Resuming cycle with {len(resume_sequence)} remaining steps')
            Logger.debug(f'CycleStateManager: MODE CHANGE - Resume sequence: {[(mode, duration) for mode, duration in resume_sequence]}')
            
            # Clear pause events
            self._pause_event.clear()
            self._resume_event.set()
            
            # Start the resume sequence
            is_manual = state_data.get('is_manual', False)
            Logger.debug(f'CycleStateManager: MODE CHANGE - Starting resume sequence, is_manual: {is_manual}')
            io_manager.process_sequence(resume_sequence, is_manual)
            
            # Clear the saved state since we're resuming
            self.clear_cycle_state()
            
            return True
            
        except Exception as e:
            Logger.error(f'CycleStateManager: Error resuming cycle: {e}')
            return False
    
    def handle_gm_fault_pause_resume(self, io_manager) -> bool:
        """
        Handle the complete pause-rest-resume cycle for GM faults.
        
        Args:
            io_manager: The IOManager instance
            
        Returns:
            bool: True if the pause/resume cycle completed successfully
        """
        try:
            Logger.info('CycleStateManager: Starting GM fault pause/resume sequence')
            
            # Step 1: Pause the current cycle
            if not self.pause_cycle(io_manager):
                Logger.error('CycleStateManager: Failed to pause cycle')
                return False
            
            # Step 2: Wait 2 seconds in rest mode to let current drop
            Logger.info('CycleStateManager: Entering 2-second rest period for current drop')
            time.sleep(2.0)
            
            # Step 3: Resume the cycle
            if not self.resume_cycle(io_manager):
                Logger.error('CycleStateManager: Failed to resume cycle')
                return False
            
            Logger.info('CycleStateManager: GM fault pause/resume sequence completed successfully')
            return True
            
        except Exception as e:
            Logger.error(f'CycleStateManager: Error in GM fault pause/resume: {e}')
            return False