import httpx
import json
from typing import Dict, Optional
from ..core.config import settings

class CurrencyService:
    """Service for handling currency operations"""
    
    def __init__(self):
        self.countries_cache = None
        self.exchange_rates_cache = {}
    
    async def get_countries_and_currencies(self) -> Dict:
        """Fetch countries and their currencies from REST Countries API"""
        if self.countries_cache:
            return self.countries_cache
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(settings.countries_api_url)
                response.raise_for_status()
                countries_data = response.json()
                
                # Process the data to extract currency information
                processed_data = {}
                for country in countries_data:
                    country_name = country.get('name', {}).get('common', '')
                    currencies = country.get('currencies', {})
                    
                    if country_name and currencies:
                        # Get the first currency (most countries have one primary currency)
                        currency_code = list(currencies.keys())[0]
                        currency_info = currencies[currency_code]
                        
                        processed_data[country_name] = {
                            'currency_code': currency_code,
                            'currency_name': currency_info.get('name', ''),
                            'currency_symbol': currency_info.get('symbol', '')
                        }
                
                self.countries_cache = processed_data
                return processed_data
                
            except Exception as e:
                print(f"Error fetching countries data: {e}")
                return {}
    
    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get exchange rate between two currencies"""
        if from_currency == to_currency:
            return 1.0
            
        cache_key = f"{from_currency}_{to_currency}"
        if cache_key in self.exchange_rates_cache:
            return self.exchange_rates_cache[cache_key]
            
        async with httpx.AsyncClient() as client:
            try:
                url = f"{settings.exchange_rate_api_url}/{from_currency}"
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                rates = data.get('rates', {})
                if to_currency in rates:
                    rate = rates[to_currency]
                    self.exchange_rates_cache[cache_key] = rate
                    return rate
                
                return None
                
            except Exception as e:
                print(f"Error fetching exchange rate: {e}")
                return None
    
    async def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """Convert amount from one currency to another"""
        rate = await self.get_exchange_rate(from_currency, to_currency)
        if rate is not None:
            return amount * rate
        return None
    
    def get_currency_for_country(self, country_name: str) -> Optional[str]:
        """Get currency code for a specific country"""
        if self.countries_cache and country_name in self.countries_cache:
            return self.countries_cache[country_name]['currency_code']
        return None

currency_service = CurrencyService()