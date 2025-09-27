#!/usr/bin/env python3
"""
Deterministic demo scenario script for Bus Dispatch RL system.
This script runs a 7-minute choreographed demo showing RL performance improvements.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any
import argparse

API_BASE = "http://localhost:8000"

class DemoOrchestrator:
    """Orchestrates the demo scenario with precise timing"""
    
    def __init__(self, api_base: str = API_BASE):
        self.api_base = api_base
        self.session = None
        self.demo_data = {
            "start_time": None,
            "events": [],
            "metrics": []
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def api_call(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make API call with error handling"""
        url = f"{self.api_base}{endpoint}"
        
        try:
            if method == "GET":
                async with self.session.get(url) as response:
                    return await response.json()
            elif method == "