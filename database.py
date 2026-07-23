"""
Database module for managing message forwarding connections
"""

import sqlite3
import logging
from typing import List, Tuple, Optional
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    """SQLite database handler for forwarding configurations"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.connection = None
        
    async def init(self) -> None:
        """Initialize database connection and create tables"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            
            # Create tables
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS forwarding_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_group_id INTEGER NOT NULL,
                    destination_group_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT 1,
                    UNIQUE(source_group_id, destination_group_id)
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_info (
                    group_id INTEGER PRIMARY KEY,
                    group_name TEXT,
                    group_username TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.connection.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    async def close(self) -> None:
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    async def add_forwarding(self, source_id: int, destination_id: int) -> bool:
        """
        Add new forwarding pair
        
        Args:
            source_id: Source group ID
            destination_id: Destination group ID
            
        Returns:
            True if added successfully, False if already exists
        """
        try:
            self.cursor.execute('''
                INSERT INTO forwarding_pairs (source_group_id, destination_group_id, active)
                VALUES (?, ?, 1)
            ''', (source_id, destination_id))
            
            self.connection.commit()
            logger.info(f"Forwarding added: {source_id} -> {destination_id}")
            return True
            
        except sqlite3.IntegrityError:
            logger.warning(f"Forwarding pair already exists: {source_id} -> {destination_id}")
            return False
        except sqlite3.Error as e:
            logger.error(f"Error adding forwarding: {e}")
            return False
    
    async def remove_forwarding(self, source_id: int, destination_id: int) -> bool:
        """
        Remove forwarding pair
        
        Args:
            source_id: Source group ID
            destination_id: Destination group ID
            
        Returns:
            True if removed successfully
        """
        try:
            self.cursor.execute('''
                DELETE FROM forwarding_pairs
                WHERE source_group_id = ? AND destination_group_id = ?
            ''', (source_id, destination_id))
            
            self.connection.commit()
            
            if self.cursor.rowcount > 0:
                logger.info(f"Forwarding removed: {source_id} -> {destination_id}")
                return True
            else:
                logger.warning(f"Forwarding pair not found: {source_id} -> {destination_id}")
                return False
                
        except sqlite3.Error as e:
            logger.error(f"Error removing forwarding: {e}")
            return False
    
    async def get_forwardings(self, source_id: int) -> List[int]:
        """
        Get all destination groups for a source group
        
        Args:
            source_id: Source group ID
            
        Returns:
            List of destination group IDs
        """
        try:
            self.cursor.execute('''
                SELECT destination_group_id FROM forwarding_pairs
                WHERE source_group_id = ? AND active = 1
            ''', (source_id,))
            
            results = self.cursor.fetchall()
            return [row[0] for row in results]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting forwardings: {e}")
            return []
    
    async def get_all_forwardings(self) -> List[Tuple[int, int]]:
        """
        Get all active forwarding pairs
        
        Returns:
            List of (source_id, destination_id) tuples
        """
        try:
            self.cursor.execute('''
                SELECT source_group_id, destination_group_id FROM forwarding_pairs
                WHERE active = 1
            ''')
            
            return self.cursor.fetchall()
            
        except sqlite3.Error as e:
            logger.error(f"Error getting all forwardings: {e}")
            return []
    
    async def save_group_info(self, group_id: int, group_name: str, group_username: Optional[str] = None) -> bool:
        """
        Save or update group information
        
        Args:
            group_id: Group ID
            group_name: Group name
            group_username: Group username (optional)
            
        Returns:
            True if successful
        """
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO group_info (group_id, group_name, group_username)
                VALUES (?, ?, ?)
            ''', (group_id, group_name, group_username))
            
            self.connection.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error saving group info: {e}")
            return False
    
    async def get_group_name(self, group_id: int) -> str:
        """
        Get group name from database
        
        Args:
            group_id: Group ID
            
        Returns:
            Group name or "Unknown Group" if not found
        """
        try:
            self.cursor.execute('''
                SELECT group_name FROM group_info WHERE group_id = ?
            ''', (group_id,))
            
            result = self.cursor.fetchone()
            return result[0] if result else f"Group {group_id}"
            
        except sqlite3.Error as e:
            logger.error(f"Error getting group name: {e}")
            return f"Group {group_id}"
    
    async def get_status(self) -> dict:
        """
        Get status information
        
        Returns:
            Dictionary with status information
        """
        try:
            self.cursor.execute('SELECT COUNT(*) FROM forwarding_pairs WHERE active = 1')
            active_count = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM group_info')
            groups_count = self.cursor.fetchone()[0]
            
            return {
                'active_forwardings': active_count,
                'tracked_groups': groups_count
            }
            
        except sqlite3.Error as e:
            logger.error(f"Error getting status: {e}")
            return {'active_forwardings': 0, 'tracked_groups': 0}
