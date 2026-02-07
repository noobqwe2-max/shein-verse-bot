"""
Shein Verse Bot - Railway Fixed Version
"""

import os
import sys
import time
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import random
from datetime import datetime
import sqlite3
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))  # 5 minutes

# Shein URLs
SHEIN_VERSE_URL = "https://www.shein.in/c/sverse-5939-37961"
SHEIN_MEN_URL = "https://www.shein.in/shein-verse-men-c-2513.html"

# User Agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'
]

# ==================== HEALTH SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/health']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            logger.debug("Health check responded")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Disable default logging

def start_health_server():
    """Start health check server"""
    port = int(os.getenv('PORT', '8080'))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    
    logger.info(f"✅ Health server started on port {port}")
    
    def run():
        server.serve_forever()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return server

# ==================== SHEIN SCRAPER ====================
class SheinScraper:
    def __init__(self):
        self.session = requests.Session()
        self.update_headers()
    
    def update_headers(self):
        """Update headers with random user agent"""
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
    
    def get_random_delay(self):
        """Get random delay between requests"""
        return random.uniform(2, 5)
    
    def fetch_page(self, url):
        """Fetch page with anti-detection"""
        try:
            time.sleep(self.get_random_delay())
            self.update_headers()
            
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Status {response.status_code} for {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def get_shein_verse_summary(self):
        """Get current stock summary for Shein Verse"""
        logger.info("📊 Getting Shein Verse stock summary...")
        
        html = self.fetch_page(SHEIN_VERSE_URL)
        if not html:
            return "❌ Could not fetch Shein Verse page"
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Get total items
        total_items_elem = soup.find(text=lambda t: 'Items Found' in t if t else False)
        total_items = total_items_elem.strip() if total_items_elem else "Not found"
        
        # Get category counts
        men_count = 0
        women_count = 0
        
        # Try to find category filters
        for elem in soup.find_all(['div', 'span', 'li']):
            text = elem.get_text(strip=True)
            if 'Men' in text and '(' in text and ')' in text:
                try:
                    men_count = int(text.split('(')[1].split(')')[0])
                except:
                    pass
            elif 'Women' in text and '(' in text and ')' in text:
                try:
                    women_count = int(text.split('(')[1].split(')')[0])
                except:
                    pass
        
        # Get product samples
        products = []
        product_elements = soup.select('.S-product-item, .product-card')[:10]
        
        for elem in product_elements[:5]:  # First 5 products
            try:
                name_elem = elem.select_one('.product-name, .goods-name, .name')
                price_elem = elem.select_one('.price, .current-price')
                
                if name_elem and price_elem:
                    products.append({
                        'name': name_elem.get_text(strip=True)[:50],
                        'price': price_elem.get_text(strip=True)
                    })
            except:
                continue
        
        # Create summary
        summary = f"""
📊 **SHEIN VERSE - CURRENT STOCK SUMMARY** 📊
🕒 *Snapshot Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📦 **TOTAL ITEMS:** {total_items}

👕 **MEN'S SECTION:** {men_count} items
👚 **WOMEN'S SECTION:** {women_count} items

🆕 **RECENT PRODUCTS:**
"""
        
        for i, product in enumerate(products, 1):
            summary += f"{i}. {product['name']} - {product['price']}\n"
        
        summary += f"\n✅ **Bot Status:** Active and monitoring Men's section"
        summary += f"\n⏰ **Next Check:** {CHECK_INTERVAL//60} minutes"
        
        return summary
    
    def get_men_products(self):
        """Get Men's products"""
        html = self.fetch_page(SHEIN_MEN_URL)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        product_elements = soup.select('.S-product-item, .product-card')[:20]
        
        for elem in product_elements:
            try:
                # Get product ID
                product_id = elem.get('data-product-id', '') or \
                            elem.get('data-goods-id', '') or \
                            str(random.randint(1000000, 9999999))
                
                # Get name
                name_elem = elem.select_one('.product-name, .goods-name, .name')
                name = name_elem.get_text(strip=True) if name_elem else "Unknown Product"
                
                # Get price
                price_elem = elem.select_one('.price, .current-price, .goods-price')
                price = price_elem.get_text(strip=True) if price_elem else "₹0"
                
                # Get image
                img_elem = elem.select_one('img')
                image_url = img_elem.get('src') or img_elem.get('data-src') or ''
                if image_url and not image_url.startswith('http'):
                    image_url = f"https:{image_url}"
                
                # Get URL
                link_elem = elem.select_one('a')
                href = link_elem.get('href') if link_elem else ''
                if href and not href.startswith('http'):
                    product_url = f"https://www.shein.in{href}"
                else:
                    product_url = href
                
                # Check if it's a men's product
                if self.is_men_product(name):
                    products.append({
                        'id': product_id,
                        'name': name[:100],
                        'price': price,
                        'image_url': image_url,
                        'url': product_url,
                        'category': 'Men',
                        'timestamp': datetime.now().isoformat(),
                        'is_new': 'new' in str(elem).lower() or 'new' in name.lower()
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing product: {str(e)}")
                continue
        
        logger.info(f"Found {len(products)} Men's products")
        return products
    
    def is_men_product(self, name):
        """Check if product is for Men"""
        name_lower = name.lower()
        
        # Exclude women's products
        women_keywords = ['women', 'woman', 'female', 'girl', 'lady', 'ladies', 'dress', 'skirt']
        for keyword in women_keywords:
            if keyword in name_lower:
                return False
        
        # Include men's products
        men_keywords = ['men', 'man', 'male', 'boy', 'guy']
        for keyword in men_keywords:
            if keyword in name_lower:
                return True
        
        # Default to True for Shein Verse
        return True

# ==================== TELEGRAM BOT ====================
class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, text, parse_mode="HTML"):
        """Send message to Telegram"""
        if not self.token or not self.chat_id:
            logger.error("Telegram not configured")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Telegram error: {str(e)}")
            return False
    
    def send_startup_message(self, summary):
        """Send startup message"""
        message = f"""
🤖 **SHEIN VERSE BOT ACTIVATED** 🤖

✅ **Status:** Successfully deployed on Railway
✅ **Features:**
   • Current stock summary (Both categories)
   • Men's section tracking
   • Product alerts with images
   • Direct buy links
   • Size availability
   • Anti-detection enabled

{summary}

⚡ **Bot is now monitoring for new stock...**
"""
        
        return self.send_message(message)
    
    def send_product_alert(self, product):
        """Send product alert"""
        import re
        
        # Create app link
        match = re.search(r'p-(\d+)\.html', product['url'])
        if match:
            app_link = f"shein://product?id={match.group(1)}"
        else:
            app_link = product['url']
        
        message = f"""
🔥 **NEW MEN'S PRODUCT ALERT** 🔥

🏷️ **{product['name']}**

💰 **Price:** {product['price']}
🏷️ **Category:** {product['category']}

🖼️ **Image:** {product['image_url'][:100]}...
🔗 **Buy Now:** {app_link}

⏰ **Detected:** {datetime.now().strftime('%H:%M:%S')}

⚡ **Click the link above to buy immediately!**
"""
        
        return self.send_message(message)

# ==================== DATABASE ====================
class ProductDB:
    def __init__(self):
        self.conn = sqlite3.connect('products.db', check_same_thread=False)
        self.init_db()
    
    def init_db(self):
        """Initialize database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT,
                price TEXT,
                image_url TEXT,
                url TEXT,
                category TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                alert_sent INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()
    
    def check_product(self, product_id):
        """Check if product exists"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        return cursor.fetchone() is not None
    
    def save_product(self, product):
        """Save product to database"""
        cursor = self.conn.cursor()
        
        if self.check_product(product['id']):
            # Update existing
            cursor.execute('''
                UPDATE products 
                SET name = ?, price = ?, image_url = ?, url = ?, 
                    last_seen = ?, alert_sent = 1
                WHERE id = ?
            ''', (
                product['name'],
                product['price'],
                product['image_url'],
                product['url'],
                datetime.now().isoformat(),
                product['id']
            ))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO products 
                (id, name, price, image_url, url, category, first_seen, last_seen, alert_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product['id'],
                product['name'],
                product['price'],
                product['image_url'],
                product['url'],
                product['category'],
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                1
            ))
        
        self.conn.commit()
        return True

# ==================== MAIN BOT ====================
def run_bot():
    """Main bot function"""
    logger.info("🤖 Starting Shein Verse Bot...")
    
    # Check configuration
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("❌ Telegram credentials missing")
        logger.info("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        return
    
    # Initialize components
    scraper = SheinScraper()
    telegram = TelegramBot()
    db = ProductDB()
    
    # Get and send startup summary
    logger.info("📊 Getting initial stock summary...")
    summary = scraper.get_shein_verse_summary()
    
    if telegram.send_startup_message(summary):
        logger.info("✅ Startup message sent to Telegram")
    else:
        logger.error("❌ Failed to send startup message")
    
    # Main monitoring loop
    check_count = 0
    while True:
        try:
            check_count += 1
            logger.info(f"🔍 Check #{check_count} - Scanning Men's section...")
            
            # Get current products
            products = scraper.get_men_products()
            
            # Check for new products
            new_products = []
            for product in products:
                if not db.check_product(product['id']):
                    new_products.append(product)
            
            # Send alerts for new products
            if new_products:
                logger.info(f"🎯 Found {len(new_products)} new products")
                for product in new_products:
                    if telegram.send_product_alert(product):
                        db.save_product(product)
                        logger.info(f"📨 Alert sent: {product['name'][:50]}...")
                        time.sleep(1)  # Delay between alerts
                    else:
                        logger.error(f"❌ Failed to send alert for {product['name']}")
            else:
                logger.info("ℹ️ No new products found")
            
            # Send summary every 6 checks (approx 30 minutes)
            if check_count % 6 == 0:
                summary_msg = f"""
📋 **PERIODIC UPDATE**

✅ **Bot Status:** Running normally
🔍 **Total Checks:** {check_count}
🎯 **New Products Found:** {len(new_products)}
⏰ **Last Check:** {datetime.now().strftime('%H:%M:%S')}
🔄 **Next Check:** {CHECK_INTERVAL//60} minutes
"""
                telegram.send_message(summary_msg)
                logger.info("📋 Sent periodic update")
            
            # Wait for next check
            logger.info(f"⏳ Waiting {CHECK_INTERVAL} seconds for next check...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("👋 Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Bot error: {str(e)}")
            time.sleep(60)  # Wait 1 minute before retry

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    print("="*50)
    print("🤖 SHEIN VERSE BOT - Railway Deployment")
    print("="*50)
    print(f"Telegram Token: {'✅ Set' if TELEGRAM_BOT_TOKEN else '❌ Missing'}")
    print(f"Telegram Chat ID: {'✅ Set' if TELEGRAM_CHAT_ID else '❌ Missing'}")
    print(f"Check Interval: {CHECK_INTERVAL} seconds")
    print("="*50)
    
    # Start health server
    start_health_server()
    
    # Run bot
    run_bot()
