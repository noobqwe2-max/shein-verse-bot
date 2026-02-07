"""
Shein Scraper with Anti-Detection
"""

import asyncio
import aiohttp
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import re

from config import Config

logger = logging.getLogger(__name__)

class SheinScraper:
    def __init__(self):
        self.session = None
        self.request_count = 0
    
    async def __aenter__(self):
        await self.create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
    
    async def create_session(self):
        """Create aiohttp session"""
        headers = {
            'User-Agent': Config.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout
        )
    
    async def close_session(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_shein_verse_products(self) -> List[Dict]:
        """Get all products from Shein Verse (both categories)"""
        return await self._fetch_products(Config.SHEIN_VERSE_URL, "all")
    
    async def get_men_products(self) -> List[Dict]:
        """Get only Men's products"""
        return await self._fetch_products(Config.SHEIN_MEN_URL, "men")
    
    async def _fetch_products(self, url: str, category: str) -> List[Dict]:
        """Fetch products from URL"""
        try:
            # Anti-detection delay
            await asyncio.sleep(Config.get_random_delay())
            
            # Rotate user agent
            if self.session:
                self.session.headers.update({'User-Agent': Config.get_random_user_agent()})
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_products(html, category)
                else:
                    logger.warning(f"Status {response.status} for {url}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return []
    
    def _parse_products(self, html: str, category: str) -> List[Dict]:
        """Parse products from HTML"""
        products = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find product items
        product_items = soup.select('.S-product-item, .product-card, [data-product-id]')
        
        for item in product_items[:100]:  # Limit to avoid rate limiting
            try:
                product = self._extract_product_info(item, category)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"Parse error: {str(e)}")
                continue
        
        logger.info(f"Parsed {len(products)} {category} products")
        return products
    
    def _extract_product_info(self, element, category: str) -> Optional[Dict]:
        """Extract product information"""
        try:
            # Get product ID
            product_id = element.get('data-product-id') or \
                        element.get('data-goods-id') or \
                        str(random.randint(1000000, 9999999))
            
            # Get name
            name_elem = element.select_one('.product-name, .goods-name, .name')
            name = name_elem.get_text(strip=True) if name_elem else "Unknown"
            
            # Get price
            price_elem = element.select_one('.price, .current-price, .goods-price')
            price = price_elem.get_text(strip=True) if price_elem else "₹0"
            
            # Clean price
            price = re.sub(r'[^\d₹.,]', '', price)
            
            # Get image
            img_elem = element.select_one('img')
            image_url = img_elem.get('src') or img_elem.get('data-src') or ''
            if image_url and not image_url.startswith('http'):
                image_url = f"https:{image_url}"
            
            # Get URL
            link_elem = element.select_one('a')
            href = link_elem.get('href') if link_elem else ''
            if href and not href.startswith('http'):
                product_url = f"https://www.shein.in{href}"
            else:
                product_url = href
            
            # Determine category if not specified
            if category == "all":
                actual_category = self._determine_category(name)
            else:
                actual_category = category
            
            return {
                'id': product_id,
                'name': name[:100],
                'price': price,
                'image_url': image_url,
                'url': product_url,
                'category': actual_category,
                'is_new': 'new' in str(element).lower() or 'new' in name.lower(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Extraction error: {str(e)}")
            return None
    
    def _determine_category(self, name: str) -> str:
        """Determine category from product name"""
        name_lower = name.lower()
        
        # Men's keywords
        men_keywords = ['men', 'man', 'male', 'boy', 'guy', 'unisex', 't-shirt', 'shirt', 'pant', 'jeans']
        # Women's keywords
        women_keywords = ['women', 'woman', 'female', 'girl', 'lady', 'dress', 'skirt', 'top', 'leggings']
        
        men_score = sum(1 for keyword in men_keywords if keyword in name_lower)
        women_score = sum(1 for keyword in women_keywords if keyword in name_lower)
        
        if men_score > women_score:
            return 'Men'
        elif women_score > men_score:
            return 'Women'
        else:
            return 'Unisex'
    
    async def get_product_details(self, product: Dict) -> Dict:
        """Get detailed product info including sizes"""
        if not product.get('url'):
            return product
        
        # Anti-detection delay
        await asyncio.sleep(random.uniform(3, 7))
        
        try:
            # Rotate user agent
            if self.session:
                self.session.headers.update({'User-Agent': Config.get_random_user_agent()})
            
            async with self.session.get(product['url']) as response:
                if response.status == 200:
                    html = await response.text()
                    sizes = self._parse_sizes(html)
                    
                    product['sizes'] = sizes
                    product['available_sizes'] = [size for size, qty in sizes.items() if qty > 0]
                    product['total_stock'] = sum(sizes.values())
                    
                    # Create size details string
                    size_details = []
                    for size, qty in sizes.items():
                        if qty > 0:
                            size_details.append(f"{size}: {qty} available")
                    
                    product['size_details'] = "\n".join(size_details) if size_details else "Check product page"
                    
        except Exception as e:
            logger.warning(f"Error getting details: {str(e)}")
            # Add default sizes
            product['sizes'] = {'S': 1, 'M': 1, 'L': 1, 'XL': 1}
            product['available_sizes'] = ['S', 'M', 'L', 'XL']
            product['total_stock'] = 4
            product['size_details'] = "S/M/L/XL (Stock unknown)"
        
        return product
    
    def _parse_sizes(self, html: str) -> Dict[str, int]:
        """Parse sizes from product page"""
        sizes = {}
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for size elements
        size_elements = soup.select(
            '.product-size-select option, '
            '.sku-item, '
            '.size-option'
        )
        
        for elem in size_elements:
            size_text = elem.get_text(strip=True)
            if size_text and len(size_text) < 10:
                # Check if available
                is_disabled = (
                    'disabled' in elem.get('class', []) or
                    'sold-out' in elem.get('class', []) or
                    elem.get('disabled') == 'disabled'
                )
                
                if not is_disabled:
                    sizes[size_text] = 1  # Default quantity
        
        # Add default sizes if none found
        if not sizes:
            sizes = {'S': 1, 'M': 1, 'L': 1, 'XL': 1}
        
        return sizes
