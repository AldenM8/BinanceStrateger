"""
交易執行器
處理下單和倉位管理
"""

import logging
from typing import Dict, Optional, Tuple
from binance.client import Client
from binance.exceptions import BinanceAPIException
from macd_strategy.core import config
from ..core.leverage_calculator import LeverageCalculator
from decimal import Decimal, ROUND_DOWN
import time

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradeExecutor:
    """交易執行器"""
    
    def __init__(self):
        """初始化交易執行器"""
        self.client = Client(config.API_KEY, config.API_SECRET)
        logger.info("使用正式網進行交易")
        self.setup_trading()
    
    def setup_trading(self) -> None:
        """設定交易環境"""
        try:
            # 設定槓桿
            self.client.futures_change_leverage(
                symbol=config.SYMBOL,
                leverage=config.LEVERAGE
            )
            logger.info(f"設定槓桿倍數: {config.LEVERAGE}x")
            
            # 設定保證金模式
            try:
                self.client.futures_change_margin_type(
                    symbol=config.SYMBOL,
                    marginType=config.MARGIN_MODE
                )
                logger.info(f"設定保證金模式: {config.MARGIN_MODE}")
            except BinanceAPIException as e:
                if e.code == -4046:
                    logger.info("保證金模式已經是正確設定，略過。")
                else:
                    logger.error(f"設定保證金模式失敗: {e}")
                    raise

        except BinanceAPIException as e:
            logger.error(f"設定交易環境失敗: {e}")
            raise
    
    def get_account_balance(self) -> float:
        """獲取帳戶餘額"""
        try:
            account = self.client.futures_account_balance()
            for balance in account:
                if balance['asset'] == 'USDT':
                    return float(balance['balance'])
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"獲取帳戶餘額失敗: {e}")
            raise
    
    def get_position_info(self) -> Optional[Dict]:
        """獲取當前持倉資訊"""
        try:
            positions = self.client.futures_position_information(symbol=config.SYMBOL)
            for position in positions:
                if float(position['positionAmt']) != 0:
                    return {
                        'side': 'LONG' if float(position['positionAmt']) > 0 else 'SHORT',
                        'size': abs(float(position['positionAmt'])),
                        'entry_price': float(position['entryPrice'])
                    }
            return None
        except BinanceAPIException as e:
            logger.error(f"獲取持倉資訊失敗: {e}")
            raise
    
    def get_current_price(self) -> float:
        """獲取當前價格"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=config.SYMBOL)
            return float(ticker['price'])
        except BinanceAPIException as e:
            logger.error(f"獲取當前價格失敗: {e}")
            raise
    
    def adjust_to_step_size(self, quantity: float) -> float:
        """將數量對齊到交易對允許的 stepSize，並移除多餘小數位"""
        info = self.client.futures_exchange_info()
        for symbol in info['symbols']:
            if symbol['symbol'] == config.SYMBOL:
                for f in symbol['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = Decimal(f['stepSize'])
                        quant = Decimal(str(quantity))
                        adjusted = (quant // step_size) * step_size
                        return float(f"{adjusted:.3f}")
        return quantity

    def adjust_price_to_tick_size(self, price: float) -> float:
        """將價格對齊到交易對允許的 tickSize，並移除多餘小數位"""
        info = self.client.futures_exchange_info()
        for symbol in info['symbols']:
            if symbol['symbol'] == config.SYMBOL:
                for f in symbol['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        tick_size = Decimal(f['tickSize'])
                        p = Decimal(str(price))
                        adjusted = (p // tick_size) * tick_size
                        return float(adjusted.quantize(tick_size, rounding=ROUND_DOWN))
        return price

    def place_order(self, side: str, quantity: float, leverage: int = None, entry_price: float = None, stop_loss: float = None, take_profit: float = None):
        """下單，可動態設定槓桿、進場價、止損、止盈"""
        try:
            # 動態設定槓桿
            if leverage is not None:
                self.client.futures_change_leverage(symbol=config.SYMBOL, leverage=leverage)
                logger.info(f"動態設定槓桿: {leverage}x")
            else:
                leverage = config.LEVERAGE
            # 取得進場價格
            if entry_price is not None:
                price = self.adjust_price_to_tick_size(entry_price)
            else:
                price = self.adjust_price_to_tick_size(self.get_current_price())
            quantity = self.adjust_to_step_size(quantity)
            logger.info(f"下單數量: {quantity}, 下單價格: {price}, 槓桿: {leverage}")
            order = self.client.futures_create_order(
                symbol=config.SYMBOL,
                side=side,
                type=config.ORDER_TYPE,
                timeInForce=config.TIME_IN_FORCE,
                quantity=quantity,
                price=price
            )
            logger.info(f"下單成功: {side} {quantity} @ {price}")
            # 止損單
            if stop_loss:
                self.client.futures_create_order(
                    symbol=config.SYMBOL,
                    side='SELL' if side == 'BUY' else 'BUY',
                    type='STOP_MARKET',
                    stopPrice=stop_loss,
                    closePosition=True
                )
                logger.info(f"設定止損: {stop_loss}")
            # 止盈單
            if take_profit:
                self.client.futures_create_order(
                    symbol=config.SYMBOL,
                    side='SELL' if side == 'BUY' else 'BUY',
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=take_profit,
                    closePosition=True
                )
                logger.info(f"設定止盈: {take_profit}")
        except BinanceAPIException as e:
            logger.error(f"下單失敗: {e}")
            raise

    def place_otoco_order(self, side: str, quantity: float, entry_price: float, stop_loss: float, take_profit: float, leverage: int = None, timeout: int = 60):
        """模擬 OTOCO 委託：主單成交後自動掛止盈/止損條件單，止盈/止損單數量用最新持倉數量"""
        try:
            # 動態設定槓桿
            if leverage is not None:
                self.client.futures_change_leverage(symbol=config.SYMBOL, leverage=leverage)
                logger.info(f"動態設定槓桿: {leverage}x")
            else:
                leverage = config.LEVERAGE
            # 主單
            quantity = self.adjust_to_step_size(quantity)
            price = self.adjust_price_to_tick_size(entry_price)
            logger.info(f"[OTOCO] 下主單: {side} {quantity} @ {price}")
            order = self.client.futures_create_order(
                symbol=config.SYMBOL,
                side=side,
                type=config.ORDER_TYPE,
                timeInForce=config.TIME_IN_FORCE,
                quantity=quantity,
                price=price
            )
            order_id = order['orderId']
            # 等主單成交
            logger.info(f"[OTOCO] 等待主單成交...")
            start = time.time()
            while time.time() - start < timeout:
                order_info = self.client.futures_get_order(symbol=config.SYMBOL, orderId=order_id)
                if order_info['status'] == 'FILLED':
                    logger.info(f"[OTOCO] 主單已成交，開始掛止盈/止損單")
                    break
                time.sleep(1)
            else:
                logger.warning(f"[OTOCO] 主單在 {timeout} 秒內未成交，停止 OTOCO 流程")
                return
            # 查詢最新持倉數量
            position = self.get_position_info()
            if not position:
                logger.error(f"[OTOCO] 主單成交後查無持倉，停止掛止盈/止損單")
                return
            close_qty = position['size']
            # 掛止盈單
            self.client.futures_create_order(
                symbol=config.SYMBOL,
                side='SELL' if side == 'BUY' else 'BUY',
                type='TAKE_PROFIT_MARKET',
                stopPrice=take_profit,
                quantity=close_qty,
                reduceOnly=True
            )
            logger.info(f"[OTOCO] 已掛止盈單: {take_profit}，數量: {close_qty}")
            # 掛止損單
            self.client.futures_create_order(
                symbol=config.SYMBOL,
                side='SELL' if side == 'BUY' else 'BUY',
                type='STOP_MARKET',
                stopPrice=stop_loss,
                quantity=close_qty,
                reduceOnly=True
            )
            logger.info(f"[OTOCO] 已掛止損單: {stop_loss}，數量: {close_qty}")
        except BinanceAPIException as e:
            logger.error(f"[OTOCO] 下單失敗: {e}")
            raise 