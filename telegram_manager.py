"""
Telegram Alert Manager
"""

import aiohttp
import asyncio
import logging
from datetime import datetime
import os
import re

from config import Config

logger = logging.getLogger(__name__)

class TelegramManager:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    async def test_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.token or not self.chat_id:
            logger.error("Telegram credentials missing")
            return False
        
        url = f"{self.base_url}/getMe"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        logger.info("✅ Telegram connection successful")
                        return True
        except Exception as e:
            logger.error(f"Telegram connection failed: {str(e)}")
        
        return False
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram"""
        if not self.token or not self.chat_id:
            logger.error("Cannot send: Telegram not configured")
            return False
        
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Send message error: {str(e)}")
            return False
    
    async def send_product_alert(self, product: Dict, is_new: bool, is_restock: bool):
        """Send product alert with all details"""
        
        # Create app link
        app_link = self._create_app_link(product['url'])
        
        # Determine alert type
        if is_new:
            alert_type = "🆕 NEW PRODUCT"
            emoji = "🔥"
        elif is_restock:
            alert_type = "🔄 RESTOCK"
            emoji = "⚡"
        else:
            alert_type = "📦 STOCK UPDATE"
            emoji = "📢"
        
        # Create message
        message = f"""
{emoji} <b>{alert_type}</b> {emoji}

🏷️ <b>{product['name']}</b>

💰 <b>Price:</b> {product['price']}
📏 <b>Sizes Available:</b>
{product.get('size_details', 'Check product page')}

📦 <b>Total Stock:</b> {product.get('total_stock', 'N/A')}

🛒 <b>BUY NOW:</b> <a href="{app_link}">Open in SHEIN App</a>
🔗 <b>Web Link:</b> <a href="{product['url']}">Click Here</a>

⏰ <i>{datetime.now().strftime('%H:%M:%S')}</i>

⚡ <b>Be quick! Limited stock!</b>
"""
        
        # Send message
        await self.send_message(message)
        
        # Send image if available
        if product.get('image_url'):
            await self.send_photo(product['image_url'], product['name'][:50])
    
    async def send_photo(self, photo_url: str, caption: str = "") -> bool:
        """Send photo to Telegram"""
        url = f"{self.base_url}/sendPhoto"
        
        payload = {
            'chat_id': self.chat_id,
            'photo': photo_url,
            'caption': caption[:100],
            'parse_mode': 'HTML'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Send photo error: {str(e)}")
            return False
    
    def _create_app_link(self, web_url: str) -> str:
        """Create deep link for SHEIN app"""
        # Extract product ID from URL
        match = re.search(r'p-(\d+)\.html', web_url)
        if match:
            product_id = match.group(1)
            return f"shein://product?id={product_id}"
        
        return web_url
    
    async def send_startup_message(self):
        """Send bot startup message"""
        message = f"""
🤖 <b>SHEIN VERSE BOT ACTIVATED</b> 🤖

✅ <b>Status:</b> Running on Railway
✅ <b>Features:</b>
   • Startup stock summary (Both categories)
   • Men's section tracking only
   • Product images & buy links
   • Size & quantity details
   • Anti-detection enabled
   • 2-hour summaries

⚡ <b>Getting current stock summary...</b>
"""
        
        await self.send_message(message)
