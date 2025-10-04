#!/usr/bin/env python3
"""
Health Monitoring Script for Production
Monitors the health of the Expense System API and external dependencies.
"""

import asyncio
import aiohttp
import time
import os
import sys
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_api_health(self):
        """Check API health endpoint"""
        try:
            async with self.session.get(f"{self.base_url}/health", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "response_time": response.headers.get("X-Process-Time", "unknown"),
                        "data": data
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_database_connectivity(self):
        """Check database connectivity through API"""
        try:
            async with self.session.get(f"{self.base_url}/api/users/me", 
                                      headers={"Authorization": "Bearer invalid"}, 
                                      timeout=10) as response:
                # We expect 401 (unauthorized) which means DB is accessible
                if response.status in [401, 422]:
                    return {"status": "healthy", "message": "Database accessible"}
                else:
                    return {"status": "unhealthy", "error": f"Unexpected status: {response.status}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_external_apis(self):
        """Check external API dependencies"""
        results = {}
        
        # Check exchange rate API
        try:
            async with self.session.get("https://api.exchangerate-api.com/v4/latest/USD", 
                                      timeout=10) as response:
                if response.status == 200:
                    results["exchange_rate_api"] = {"status": "healthy"}
                else:
                    results["exchange_rate_api"] = {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            results["exchange_rate_api"] = {"status": "unhealthy", "error": str(e)}
        
        # Check countries API
        try:
            async with self.session.get("https://restcountries.com/v3.1/all?fields=name,currencies&limit=1", 
                                      timeout=10) as response:
                if response.status == 200:
                    results["countries_api"] = {"status": "healthy"}
                else:
                    results["countries_api"] = {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            results["countries_api"] = {"status": "unhealthy", "error": str(e)}
        
        return results
    
    async def run_health_check(self):
        """Run complete health check"""
        logger.info("🏥 Starting health check...")
        
        start_time = time.time()
        
        # Run all checks concurrently
        api_health, db_health, external_apis = await asyncio.gather(
            self.check_api_health(),
            self.check_database_connectivity(),
            self.check_external_apis(),
            return_exceptions=True
        )
        
        end_time = time.time()
        
        # Compile results
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_check_time": round(end_time - start_time, 2),
            "overall_status": "healthy",
            "components": {
                "api": api_health if not isinstance(api_health, Exception) else {"status": "error", "error": str(api_health)},
                "database": db_health if not isinstance(db_health, Exception) else {"status": "error", "error": str(db_health)},
                "external_apis": external_apis if not isinstance(external_apis, Exception) else {"status": "error", "error": str(external_apis)}
            }
        }
        
        # Determine overall status
        for component in results["components"].values():
            if isinstance(component, dict):
                if component.get("status") != "healthy":
                    results["overall_status"] = "degraded"
                    break
            else:
                # External APIs are a dict of services
                for service in component.values():
                    if service.get("status") != "healthy":
                        results["overall_status"] = "degraded"
                        break
        
        return results

async def main():
    """Main monitoring function"""
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    async with HealthMonitor(base_url) as monitor:
        results = await monitor.run_health_check()
        
        # Print results
        print(json.dumps(results, indent=2))
        
        # Log summary
        status = results["overall_status"]
        if status == "healthy":
            logger.info("✅ All systems healthy")
            sys.exit(0)
        elif status == "degraded":
            logger.warning("⚠️ Some systems degraded")
            sys.exit(1)
        else:
            logger.error("❌ System unhealthy")
            sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())