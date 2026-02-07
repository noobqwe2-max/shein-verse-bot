"""
Main Shein Verse Bot - Railway Compatible
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
import signal
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('shein_bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from shein_scraper import SheinScraper
from telegram_manager import TelegramManager
from product_database import ProductDatabase

# Health check server
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def start_health_server():
    """Start health check server in separate thread"""
    port = int(os.getenv('PORT', '8080'))
    
    def run_server():
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        logger.info(f"🌐 Health server started on port {port}")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

class SheinVerseBot:
    def __init__(self):
        self.scraper = SheinScraper()
        self.telegram = TelegramManager()
        self.db = ProductDatabase()
        self.is_running = False
        self.check_count = 0
        self.stats = {
            'total_checks': 0,
            'products_found': 0,
            'alerts_sent': 0,
            'start_time': datetime.now()
        }
    
    async def get_current_stock_summary(self):
        """Get current stock summary for both categories on startup"""
        logger.info("📊 Getting current stock summary...")
        
        try:
            # Get all products from Shein Verse
            all_products = await self.scraper.get_shein_verse_products()
            
            if not all_products:
                return "No products found"
            
            # Categorize products
            men_products = [p for p in all_products if p.get('category') == 'Men']
            women_products = [p for p in all_products if p.get('category') == 'Women']
            
            # Calculate statistics
            total_products = len(all_products)
            total_men = len(men_products)
            total_women = len(women_products)
            
            # Get price ranges
            men_prices = [float(p.get('price', 0).replace('₹', '').replace(',', '')) 
                         for p in men_products if p.get('price')]
            women_prices = [float(p.get('price', 0).replace('₹', '').replace(',', '')) 
                           for p in women_products if p.get('price')]
            
            avg_men_price = sum(men_prices) / len(men_prices) if men_prices else 0
            avg_women_price = sum(women_prices) / len(women_prices) if women_prices else 0
            
            # Get new products (last 24 hours)
            twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
            new_men = [p for p in men_products if p.get('is_new', False)]
            new_women = [p for p in women_products if p.get('is_new', False)]
            
            # Create summary message
            summary = f"""
📊 **SHEIN VERSE - CURRENT STOCK SUMMARY** 📊
🕒 *Snapshot Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📦 **TOTAL PRODUCTS:** {total_products}

👕 **MEN'S SECTION:**
   • Total Items: {total_men}
   • New Today: {len(new_men)}
   • Avg Price: ₹{avg_men_price:.2f}
   • Price Range: ₹{min(men_prices) if men_prices else 0} - ₹{max(men_prices) if men_prices else 0}

👚 **WOMEN'S SECTION:**
   • Total Items: {total_women}
   • New Today: {len(new_women)}
   • Avg Price: ₹{avg_women_price:.2f}
   • Price Range: ₹{min(women_prices) if women_prices else 0} - ₹{max(women_prices) if women_prices else 0}

🏷️ **TOP 5 NEW ARRIVALS (Men):**
"""
            
            # Add top 5 new men's products
            new_men_sorted = sorted(new_men, 
                                   key=lambda x: float(x.get('price', '0').replace('₹', '').replace(',', '')), 
                                   reverse=True)[:5]
            
            for i, product in enumerate(new_men_sorted, 1):
                price = product.get('price', '₹0')
                name = product.get('name', 'Unknown')[:40]
                summary += f"{i}. {name}... - {price}\n"
            
            summary += f"\n🔍 **Bot will now track ONLY Men's section for new/restocked items.**"
            summary += f"\n✅ **Tracking Started:** {datetime.now().strftime('%H:%M:%S')}"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting stock summary: {str(e)}")
            return f"Error getting stock summary: {str(e)}"
    
    async def initialize(self):
        """Initialize the bot"""
        logger.info("🚀 Starting Shein Verse Bot...")
        
        # Test Telegram connection
        if not await self.telegram.test_connection():
            logger.error("❌ Telegram connection failed")
            return False
        
        # Send startup message
        await self.telegram.send_startup_message()
        
        # Get and send current stock summary
        stock_summary = await self.get_current_stock_summary()
        await self.telegram.send_message(stock_summary)
        
        # Initial scan for men's products
        await self.scan_men_products()
        
        self.is_running = True
        logger.info("✅ Bot initialized successfully")
        return True
    
    async def scan_men_products(self):
        """Scan for Men's products only"""
        try:
            logger.info("🔍 Scanning Men's section...")
            
            # Get men's products
            men_products = await self.scraper.get_men_products()
            
            if not men_products:
                logger.warning("⚠️ No Men's products found")
                return
            
            logger.info(f"📊 Found {len(men_products)} Men's products")
            
            alerts_sent = 0
            for product in men_products:
                # Get detailed info with sizes
                detailed_product = await self.scraper.get_product_details(product)
                
                # Check if new or restocked
                is_new, is_restock = await self.db.check_product(detailed_product)
                
                if is_new or is_restock:
                    # Send alert with all details
                    await self.telegram.send_product_alert(detailed_product, is_new, is_restock)
                    
                    # Save to database
                    await self.db.save_product(detailed_product, is_new, is_restock)
                    
                    alerts_sent += 1
                    self.stats['alerts_sent'] += 1
                    
                    # Anti-detection delay
                    await asyncio.sleep(2)
            
            self.stats['total_checks'] += 1
            self.stats['products_found'] = len(men_products)
            
            logger.info(f"✅ Scan complete. Sent {alerts_sent} alerts")
            
        except Exception as e:
            logger.error(f"❌ Scan error: {str(e)}")
    
    async def send_periodic_summary(self):
        """Send periodic summary every 2 hours"""
        stats = await self.db.get_stats()
        
        summary = f"""
📋 **SHEIN VERSE - PERIODIC SUMMARY**
🕒 {datetime.now().strftime('%H:%M:%S')}

📊 **Statistics:**
• Total Checks: {self.stats['total_checks']}
• Products Found: {self.stats['products_found']}
• Alerts Sent: {self.stats['alerts_sent']}
• New Today: {stats.get('new_today', 0)}
• Restocks Today: {stats.get('restocks_today', 0)}

🎯 **Currently Tracking:** Men's Section Only
⚡ **Next Check:** {(datetime.now() + timedelta(minutes=Config.CHECK_INTERVAL)).strftime('%H:%M')}
"""
        
        await self.telegram.send_message(summary)
        logger.info("📋 Sent periodic summary")
    
    async def run(self):
        """Main bot loop"""
        last_summary_time = datetime.now()
        summary_interval = timedelta(hours=2)
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Scan for products
                await self.scan_men_products()
                
                # Send summary every 2 hours
                if current_time - last_summary_time >= summary_interval:
                    await self.send_periodic_summary()
                    last_summary_time = current_time
                
                # Wait for next check with random delay
                interval_seconds = Config.CHECK_INTERVAL * 60
                jitter = random.randint(-30, 30)
                wait_time = max(60, interval_seconds + jitter)
                
                logger.info(f"⏳ Next check in {wait_time//60} minutes")
                await asyncio.sleep(wait_time)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Main loop error: {str(e)}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Stop the bot"""
        self.is_running = False
        await self.telegram.send_message("🛑 Bot stopped gracefully")
        logger.info("👋 Bot stopped")

async def main():
    """Main function"""
    # Start health server
    health_thread = start_health_server()
    
    # Create bot instance
    bot = SheinVerseBot()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} received")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and run bot
        if await bot.initialize():
            await bot.run()
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await bot.stop()

if __name__ == "__main__":
    # Check environment variables
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        print("❌ ERROR: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        print("1. Create bot with @BotFather")
        print("2. Get chat ID from @userinfobot")
        print("3. Set variables in Railway dashboard")
        sys.exit(1)
    
    print("="*50)
    print("🤖 SHEIN VERSE BOT - Starting...")
    print("="*50)
    
    # Run the bot
    asyncio.run(main())
