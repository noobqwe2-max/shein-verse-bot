"""
Product Database
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from config import Config

logger = logging.getLogger(__name__)

class ProductDatabase:
    def __init__(self, db_path: str = Config.DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price TEXT,
                image_url TEXT,
                url TEXT NOT NULL,
                category TEXT,
                sizes TEXT,
                total_stock INTEGER,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                last_alert TIMESTAMP,
                alert_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                alert_type TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def check_product(self, product: Dict) -> Tuple[bool, bool]:
        """Check if product is new or restocked"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, total_stock FROM products WHERE id = ?",
            (product['id'],)
        )
        
        existing = cursor.fetchone()
        conn.close()
        
        if not existing:
            return True, False  # New product
        
        # Check for restock
        old_stock = existing[1] or 0
        new_stock = product.get('total_stock', 0)
        
        is_restock = (old_stock == 0 and new_stock > 0)
        
        return False, is_restock
    
    async def save_product(self, product: Dict, is_new: bool, is_restock: bool):
        """Save product to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        sizes_json = json.dumps(product.get('sizes', {}))
        
        if is_new:
            # Insert new product
            cursor.execute('''
                INSERT INTO products 
                (id, name, price, image_url, url, category, sizes, total_stock, first_seen, last_seen, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product['id'],
                product['name'],
                product.get('price', ''),
                product.get('image_url', ''),
                product['url'],
                product.get('category', 'Men'),
                sizes_json,
                product.get('total_stock', 0),
                now,
                now,
                1
            ))
        else:
            # Update existing product
            cursor.execute('''
                UPDATE products 
                SET name = ?, price = ?, image_url = ?, url = ?, 
                    sizes = ?, total_stock = ?, last_seen = ?, is_active = 1
                WHERE id = ?
            ''', (
                product['name'],
                product.get('price', ''),
                product.get('image_url', ''),
                product['url'],
                sizes_json,
                product.get('total_stock', 0),
                now,
                product['id']
            ))
        
        # Record alert
        if is_new or is_restock:
            alert_type = 'new' if is_new else 'restock'
            
            cursor.execute('''
                INSERT INTO alerts (product_id, alert_type, timestamp)
                VALUES (?, ?, ?)
            ''', (product['id'], alert_type, now))
            
            # Update alert count
            cursor.execute('''
                UPDATE products 
                SET last_alert = ?, alert_count = alert_count + 1 
                WHERE id = ?
            ''', (now, product['id']))
        
        conn.commit()
        conn.close()
    
    async def get_stats(self) -> Dict:
        """Get bot statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total products
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        total_products = cursor.fetchone()[0]
        
        # New today
        today = datetime.now().date().isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM alerts 
            WHERE alert_type = 'new' AND DATE(timestamp) = ?
        ''', (today,))
        new_today = cursor.fetchone()[0]
        
        # Restocks today
        cursor.execute('''
            SELECT COUNT(*) FROM alerts 
            WHERE alert_type = 'restock' AND DATE(timestamp) = ?
        ''', (today,))
        restocks_today = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_products': total_products,
            'new_today': new_today,
            'restocks_today': restocks_today
  }
