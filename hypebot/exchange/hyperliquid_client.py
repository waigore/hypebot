"""Hyperliquid exchange client for trading operations."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import asyncio
import httpx

from .models import Order, Trade, AccountBalance
from ..config import HyperliquidConfig


logger = logging.getLogger(__name__)


class HyperliquidClient:
    """Client for interacting with Hyperliquid exchange."""
    
    def __init__(self, config: HyperliquidConfig):
        """Initialize Hyperliquid client."""
        self.config = config
        self.api_key = config.api_key
        self.secret_key = config.secret_key
        self.testnet = config.testnet
        self.base_url = config.base_url or self._get_base_url()
        self._client: Optional[httpx.AsyncClient] = None
        self._session_id: Optional[str] = None
    
    def _get_base_url(self) -> str:
        """Get appropriate base URL based on testnet setting."""
        if self.testnet:
            return "https://api.hyperliquid-testnet.xyz"
        else:
            return "https://api.hyperliquid.xyz"
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "HypeBot/1.0.0"
                }
            )
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Hyperliquid API."""
        try:
            await self._ensure_client()
            
            # Add authentication headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Signature": self._generate_signature(data or {})
            }
            
            if method.upper() == "GET":
                response = await self._client.get(endpoint, params=params, headers=headers)
            elif method.upper() == "POST":
                response = await self._client.post(endpoint, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            raise
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate signature for API authentication."""
        # This is a simplified signature generation
        # In a real implementation, you would use the proper Hyperliquid signing method
        import hashlib
        import hmac
        
        message = str(data)
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def get_account_info(self) -> Optional[AccountBalance]:
        """Get account information and balance."""
        try:
            response = await self._make_request("GET", "/info")
            
            if "accountValue" in response:
                return AccountBalance(
                    asset="USDC",  # Assuming USDC as base currency
                    free=float(response.get("accountValue", 0)),
                    locked=0.0,  # Hyperliquid doesn't have locked balance concept
                    total=float(response.get("accountValue", 0)),
                    timestamp=datetime.utcnow()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        try:
            response = await self._make_request("GET", "/info")
            
            positions = []
            if "assetPositions" in response:
                for pos in response["assetPositions"]:
                    positions.append({
                        "symbol": pos.get("coin", ""),
                        "size": float(pos.get("position", {}).get("szi", 0)),
                        "entry_price": float(pos.get("position", {}).get("entryPx", 0)),
                        "unrealized_pnl": float(pos.get("unrealizedPnl", 0)),
                        "side": "LONG" if float(pos.get("position", {}).get("szi", 0)) > 0 else "SHORT"
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def place_order(
        self, 
        symbol: str, 
        side: str, 
        order_type: str, 
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Optional[Order]:
        """Place a trading order."""
        try:
            # Map order types
            order_type_map = {
                "MARKET": "Market",
                "LIMIT": "Limit",
                "STOP": "Stop"
            }
            
            # Map sides
            side_map = {
                "BUY": "B",
                "SELL": "S"
            }
            
            order_data = {
                "coin": symbol,
                "is_buy": side_map.get(side, "B"),
                "sz": str(quantity),
                "limit_px": str(price) if price else "0",
                "order_type": order_type_map.get(order_type, "Limit"),
                "reduce_only": False,
                "cloid": f"hypebot_{int(datetime.utcnow().timestamp())}"
            }
            
            response = await self._make_request("POST", "/exchange", data=order_data)
            
            if "status" in response and response["status"] == "ok":
                order = Order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                    order_id=response.get("response", {}).get("data", {}).get("oid"),
                    status="PENDING",
                    timestamp=datetime.utcnow()
                )
                
                logger.info(f"Order placed successfully: {order.order_id}")
                return order
            else:
                logger.error(f"Failed to place order: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        try:
            cancel_data = {
                "oid": order_id
            }
            
            response = await self._make_request("POST", "/exchange", data=cancel_data)
            
            if "status" in response and response["status"] == "ok":
                logger.info(f"Order {order_id} cancelled successfully")
                return True
            else:
                logger.error(f"Failed to cancel order {order_id}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an order."""
        try:
            response = await self._make_request("GET", f"/info?oid={order_id}")
            
            if "orders" in response:
                for order in response["orders"]:
                    if order.get("oid") == order_id:
                        return {
                            "order_id": order_id,
                            "status": order.get("status", "UNKNOWN"),
                            "filled_quantity": float(order.get("sz", 0)),
                            "average_fill_price": float(order.get("avgPx", 0)),
                            "timestamp": datetime.utcnow()
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {e}")
            return None
    
    async def get_trades(self, symbol: Optional[str] = None) -> List[Trade]:
        """Get recent trades."""
        try:
            params = {}
            if symbol:
                params["coin"] = symbol
            
            response = await self._make_request("GET", "/info", params=params)
            
            trades = []
            if "fills" in response:
                for fill in response["fills"]:
                    trade = Trade(
                        trade_id=fill.get("tid", ""),
                        symbol=fill.get("coin", ""),
                        side="BUY" if fill.get("dir") == "B" else "SELL",
                        quantity=float(fill.get("sz", 0)),
                        price=float(fill.get("px", 0)),
                        timestamp=datetime.fromtimestamp(fill.get("time", 0) / 1000),
                        order_id=fill.get("oid", ""),
                        commission=float(fill.get("fee", 0)),
                        commission_asset="USDC"
                    )
                    trades.append(trade)
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for a symbol."""
        try:
            response = await self._make_request("GET", f"/info?coin={symbol}")
            
            if "meta" in response and "universe" in response["meta"]:
                for coin_info in response["meta"]["universe"]:
                    if coin_info.get("name") == symbol:
                        return {
                            "symbol": symbol,
                            "price": float(coin_info.get("maxLeverage", 0)),  # This would be actual price in real implementation
                            "volume_24h": 0.0,  # Not available in this endpoint
                            "timestamp": datetime.utcnow()
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Get funding rate for a symbol."""
        try:
            response = await self._make_request("GET", "/info")
            
            if "meta" in response and "universe" in response["meta"]:
                for coin_info in response["meta"]["universe"]:
                    if coin_info.get("name") == symbol:
                        return float(coin_info.get("funding", 0))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting funding rate for {symbol}: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """Test connection to Hyperliquid API."""
        try:
            response = await self._make_request("GET", "/info")
            return "accountValue" in response or "meta" in response
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
