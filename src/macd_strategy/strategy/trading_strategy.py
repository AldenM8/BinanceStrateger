"""
MACD 短線交易策略主程式
整合數據獲取、指標計算、信號分析和交易執行
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import time
import os

from ..core import config
from ..data.data_provider import DataProvider
from ..indicators.technical_indicators import TechnicalIndicators, SignalAnalyzer

# 設定日誌
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Position:
    """持倉資訊"""
    
    def __init__(self, side: str, entry_price: float, size: float, 
                 stop_loss: float, take_profit: float, timestamp: datetime):
        """
        初始化持倉
        
        Args:
            side: 方向 ('long' 或 'short')
            entry_price: 進場價格
            size: 倉位大小
            stop_loss: 停損價格
            take_profit: 停利價格
            timestamp: 進場時間
        """
        self.side = side
        self.entry_price = entry_price
        self.size = size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.timestamp = timestamp
        self.exit_price = None
        self.exit_timestamp = None
        self.pnl = 0.0
        self.status = 'open'  # open, closed
    
    def close_position(self, exit_price: float, exit_timestamp: datetime):
        """
        平倉
        
        Args:
            exit_price: 出場價格
            exit_timestamp: 出場時間
        """
        self.exit_price = exit_price
        self.exit_timestamp = exit_timestamp
        self.status = 'closed'
        
        # 計算損益
        if self.side == 'long':
            self.pnl = (exit_price - self.entry_price) * self.size
        else:
            self.pnl = (self.entry_price - exit_price) * self.size
    
    def check_stop_conditions(self, current_price: float) -> Optional[str]:
        """
        檢查是否觸發停損或停利
        
        Args:
            current_price: 當前價格
            
        Returns:
            觸發條件 ('stop_loss', 'take_profit', None)
        """
        if self.side == 'long':
            if current_price <= self.stop_loss:
                return 'stop_loss'
            elif current_price >= self.take_profit:
                return 'take_profit'
        else:
            if current_price >= self.stop_loss:
                return 'stop_loss'
            elif current_price <= self.take_profit:
                return 'take_profit'
        
        return None
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'size': self.size,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.timestamp.isoformat(),
            'exit_time': self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            'pnl': self.pnl,
            'status': self.status
        }


class MacdTradingStrategy:
    """MACD 短線交易策略"""
    
    def __init__(self):
        """
        初始化交易策略
        """
        self.symbol = config.SYMBOL
        self.data_provider = DataProvider(config.EXCHANGE)
        self.signal_analyzer = SignalAnalyzer(config.MIN_CONSECUTIVE_BARS)
        
        # 交易狀態
        self.positions: List[Position] = []
        self.current_position: Optional[Position] = None
        self.total_pnl = 0.0
        self.trade_count = 0
        self.win_count = 0
        
        # 數據快取
        self.data_4h = None
        self.data_1h = None
        self.last_update = None
        
        # 設定監控模式的日誌文件
        self._setup_monitor_logging()
        
        logger.info(f"MACD 交易策略初始化完成 - 交易對: {self.symbol}")
    
    def _setup_monitor_logging(self):
        """設定監控模式的日誌文件"""
        # 確保logs目錄存在
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # 生成帶時間戳的日誌文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"monitor_{timestamp}.log"
        log_filepath = os.path.join(logs_dir, log_filename)
        
        # 為monitor logger添加文件處理器
        monitor_logger = logging.getLogger(__name__)
        
        # 檢查是否已經有文件處理器，避免重複添加
        has_file_handler = any(isinstance(handler, logging.FileHandler) 
                              for handler in monitor_logger.handlers)
        
        if not has_file_handler:
            file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
            monitor_logger.addHandler(file_handler)
            
            logger.info(f"監控日誌文件已設定: {log_filepath}")
    
    def analyze_signal(self, data_1h: pd.DataFrame, data_4h: pd.DataFrame) -> str:
        """
        分析交易信號（簡化版本，用於回測）
        
        Args:
            data_1h: 1小時數據
            data_4h: 4小時數據
            
        Returns:
            信號 ('BUY', 'SELL', 'HOLD')
        """
        try:
            # 檢查數據有效性
            if data_1h is None or data_4h is None or len(data_1h) < 50 or len(data_4h) < 50:
                return 'HOLD'
            
            # 使用信號分析器檢查做多信號 - 修正參數順序
            long_signal = self.signal_analyzer.analyze_long_signal(data_4h, data_1h)
            if long_signal.get('signal', False):
                return 'BUY'
            
            # 檢查做空信號 - 修正參數順序
            short_signal = self.signal_analyzer.analyze_short_signal(data_4h, data_1h)
            if short_signal.get('signal', False):
                return 'SELL'
            
            return 'HOLD'
            
        except Exception as e:
            logger.error(f"信號分析失敗: {e}")
            return 'HOLD'
    
    def update_market_data(self, warmup_bars=100) -> bool:
        """
        更新市場數據
        
        Args:
            warmup_bars: 預熱數據量（確保技術指標準確）
        
        Returns:
            是否成功更新數據
        """
        try:
            # 獲取足夠的歷史數據以確保技術指標準確
            required_4h = 200 + warmup_bars
            required_1h = 500 + warmup_bars
            
            # 獲取 4小時數據
            data_4h_raw = self.data_provider.get_ohlcv_data(
                self.symbol, config.TIMEFRAME_4H, required_4h
            )
            if data_4h_raw is None:
                logger.error("無法獲取 4小時數據")
                return False
            
            # 獲取 1小時數據
            data_1h_raw = self.data_provider.get_ohlcv_data(
                self.symbol, config.TIMEFRAME_1H, required_1h
            )
            if data_1h_raw is None:
                logger.error("無法獲取 1小時數據")
                return False
            
            # 計算技術指標（使用完整數據）
            self.data_4h = TechnicalIndicators.calculate_macd(
                data_4h_raw, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL
            )
            
            self.data_1h = TechnicalIndicators.calculate_macd(
                data_1h_raw, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL
            )
            self.data_1h = TechnicalIndicators.calculate_atr(
                self.data_1h, config.ATR_PERIOD
            )
            
            # 只保留最新的數據（去除過多的歷史數據）
            self.data_4h = self.data_4h.tail(200)
            self.data_1h = self.data_1h.tail(500)
            
            self.last_update = datetime.now()
            logger.debug(f"市場數據更新完成 - 4H: {len(self.data_4h)} 筆, 1H: {len(self.data_1h)} 筆")
            return True
            
        except Exception as e:
            logger.error(f"更新市場數據失敗: {e}")
            return False
    
    def check_entry_signals(self) -> Optional[dict]:
        """
        檢查進場信號
        
        Returns:
            信號資訊字典或 None
        """
        if self.data_4h is None or self.data_1h is None:
            return None
        
        # 如果已有持倉，不檢查新信號
        if self.current_position is not None:
            return None
        
        # 檢查做多信號
        long_signal = self.signal_analyzer.analyze_long_signal(self.data_4h, self.data_1h)
        if long_signal['signal']:
            logger.info("檢測到做多信號")
            return {**long_signal, 'side': 'long'}
        
        # 檢查做空信號
        short_signal = self.signal_analyzer.analyze_short_signal(self.data_4h, self.data_1h)
        if short_signal['signal']:
            logger.info("檢測到做空信號")
            return {**short_signal, 'side': 'short'}
        
        return None
    
    def execute_entry(self, signal: dict) -> bool:
        """
        執行進場
        
        Args:
            signal: 信號資訊
            
        Returns:
            是否成功進場
        """
        try:
            # 獲取當前價格作為進場價
            current_price = self.data_provider.get_current_price(self.symbol)
            if current_price is None:
                current_price = self.data_1h['close'].iloc[-1]
            
            # 獲取ATR用於計算停損停利
            atr = signal.get('atr', self.data_1h['atr'].iloc[-1])
            
            # 計算停損停利
            if signal['side'] == 'long':
                stop_loss = current_price - (atr * config.STOP_LOSS_MULTIPLIER)
                take_profit = current_price + (atr * config.STOP_LOSS_MULTIPLIER * config.RISK_REWARD_RATIO)
            else:  # short
                stop_loss = current_price + (atr * config.STOP_LOSS_MULTIPLIER)
                take_profit = current_price - (atr * config.STOP_LOSS_MULTIPLIER * config.RISK_REWARD_RATIO)
            
            # 計算倉位大小
            position_size = config.POSITION_SIZE
            
            # 建立持倉
            position = Position(
                side=signal['side'],
                entry_price=current_price,
                size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.now()
            )
            
            self.current_position = position
            self.positions.append(position)
            
            logger.info(f"進場執行成功 - {signal['side'].upper()} "
                       f"價格: {current_price:.4f} "
                       f"停損: {stop_loss:.4f} "
                       f"停利: {take_profit:.4f}")
            
            return True
            
        except Exception as e:
            logger.error(f"執行進場失敗: {e}")
            return False
    
    def check_exit_conditions(self, use_realtime_price: bool = True) -> Optional[str]:
        """
        檢查出場條件
        
        Args:
            use_realtime_price: 是否使用即時價格（高頻模式建議使用）
        
        Returns:
            出場原因或 None
        """
        if self.current_position is None:
            return None
        
        # 獲取當前價格
        if use_realtime_price:
            # 嘗試獲取即時價格
            current_price = self.data_provider.get_current_price(self.symbol)
            if current_price is None:
                # 如果無法獲取即時價格，使用最新的收盤價
                current_price = self.data_1h['close'].iloc[-1]
                logger.debug(f"使用最新收盤價: {current_price:.4f}")
            else:
                logger.debug(f"使用即時價格: {current_price:.4f}")
        else:
            # 使用最新的收盤價
            current_price = self.data_1h['close'].iloc[-1]
        
        # 檢查停損停利
        stop_condition = self.current_position.check_stop_conditions(current_price)
        if stop_condition:
            return stop_condition
        
        return None
    
    def execute_exit(self, reason: str) -> bool:
        """
        執行出場
        
        Args:
            reason: 出場原因
            
        Returns:
            是否成功出場
        """
        try:
            if self.current_position is None:
                return False
            
            # 獲取當前價格
            current_price = self.data_provider.get_current_price(self.symbol)
            if current_price is None:
                current_price = self.data_1h['close'].iloc[-1]
            
            # 平倉
            self.current_position.close_position(current_price, datetime.now())
            
            # 更新統計
            self.total_pnl += self.current_position.pnl
            self.trade_count += 1
            if self.current_position.pnl > 0:
                self.win_count += 1
            
            logger.info(f"出場執行成功 - {reason.upper()} "
                       f"價格: {current_price:.4f} "
                       f"損益: {self.current_position.pnl:.4f}")
            
            self.current_position = None
            return True
            
        except Exception as e:
            logger.error(f"執行出場失敗: {e}")
            return False
    
    def run_strategy(self, duration_hours: float = 24) -> dict:
        """
        運行 MACD 交易策略（信號監測模式）
        - 每小時整點：開始檢查進場信號，持續重試直到獲得正確時間的數據
        - 純提醒模式：不執行實際交易，只提供信號提醒
        
        Args:
            duration_hours: 運行時長（小時）
            
        Returns:
            策略運行結果
        """
        
        logger.info(f"開始運行 MACD 信號監測，預計運行 {duration_hours} 小時")
        logger.info(f"監測頻率：每小時整點檢查進場信號，持續重試直到獲得正確數據")
        logger.info(f"模式：純信號提醒，不執行實際交易")
        print(f"🚀 啟動 MACD 信號監測，預計運行 {duration_hours} 小時")
        print(f"⚡ 監測模式：每小時整點檢查進場信號")
        print(f"📢 純提醒模式：檢測到信號時會提醒，手動下單後讓幣安自動執行")
        print(f"🎯 交易對：{self.symbol}")
        print("-" * 80)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        
        last_entry_check_hour = -1  # 記錄上次檢查進場信號的小時
        signal_count = 0  # 信號計數器
        
        while datetime.now() < end_time:
            try:
                current_time = datetime.now()
                current_hour = current_time.hour
                current_minute = current_time.minute
                
                # 每小時1秒時檢查進場信號
                current_second = current_time.second
                if (current_minute == 0 and current_second == 1 and current_hour != last_entry_check_hour):
                    # 記錄檢查開始
                    check_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"⏰ {check_time_str} - 開始執行每小時信號檢查")
                    print(f"\n⏰ {check_time_str} - 檢查信號")
                    
                    # 持續嘗試獲取正確的數據
                    data_acquired = False
                    retry_count = 0
                    max_retries = 10  # 最多重試10次
                    
                    while not data_acquired and retry_count < max_retries:
                        retry_count += 1
                        
                        if retry_count > 1:
                            logger.info(f"📡 第 {retry_count} 次嘗試獲取數據...")
                            # print(f"📡 第 {retry_count} 次嘗試獲取數據...")
                        else:
                            logger.info("📡 開始更新市場數據...")
                            # print("📡 開始更新市場數據...")
                        
                        if self.update_market_data():
                            # 驗證數據時間是否正確
                            data_validation = self._validate_data_timing(current_time)
                            
                            if data_validation['valid']:
                                logger.info("✅ 市場數據更新成功，數據時間驗證通過")
                                logger.info(f"📅 數據時間範圍: {data_validation['data_info']}")
                                data_acquired = True
                                
                                # 獲取當前價格信息
                                current_price = self.data_provider.get_current_price(self.symbol)
                                
                                # 獲取1小時K線數據（已完成的）
                                latest_1h_open = self.data_1h['open'].iloc[-2]
                                latest_1h_high = self.data_1h['high'].iloc[-2]
                                latest_1h_low = self.data_1h['low'].iloc[-2]
                                latest_1h_close = self.data_1h['close'].iloc[-2]
                                
                                # 獲取已完成K線的 MACD 數據（用於交易判斷）
                                latest_1h_macd = self.data_1h['macd_histogram'].iloc[-2]  # 已完成的1小時K線
                                prev_1h_macd = self.data_1h['macd_histogram'].iloc[-3] if len(self.data_1h) > 2 else 0
                                latest_4h_macd = self.data_4h['macd_histogram'].iloc[-1]  # 4小時當前進行中的
                                
                                # 獲取1小時K線時間範圍
                                latest_1h_time = self.data_1h.index[-2]
                                if hasattr(latest_1h_time, 'tz') and latest_1h_time.tz is not None:
                                    latest_1h_time = latest_1h_time.tz_localize(None)
                                latest_1h_time_local = latest_1h_time + timedelta(hours=8)
                                time_range_str = f"{latest_1h_time_local.strftime('%H:%M')}-{(latest_1h_time_local + timedelta(hours=1)).strftime('%H:%M')}"
                                
                                # 簡化輸出：只顯示關鍵信息
                                print(f"📊 1H [{time_range_str}] OHLC: ${latest_1h_open:.2f}/{latest_1h_high:.2f}/{latest_1h_low:.2f}/{latest_1h_close:.2f}")
                                print(f"📈 1H MACD: 當前={latest_1h_macd:.4f}, 前根={prev_1h_macd:.4f}")
                                print(f"📈 4H MACD: {latest_4h_macd:.4f}")
                                
                                logger.info(f"💰 當前市場價格:")
                                logger.info(f"   即時價格: ${current_price:.4f}" if current_price else "   即時價格: 獲取失敗")
                                logger.info(f"📊 MACD 指標狀態:")
                                logger.info(f"   1H MACD 直方圖: {latest_1h_macd:.6f}")
                                logger.info(f"   4H MACD 直方圖: {latest_4h_macd:.6f}")
                                
                                # 檢查進場信號
                                logger.info("🔍 開始分析進場信號...")
                                
                                signal = self.check_entry_signals()
                                if signal:
                                    signal_count += 1
                                    
                                    # 獲取當前價格用於計算建議價格
                                    current_price = self.data_provider.get_current_price(self.symbol)
                                    if current_price is None:
                                        current_price = self.data_1h['close'].iloc[-1]
                                    
                                    # 獲取ATR並計算建議的停損停利
                                    atr = signal.get('atr', self.data_1h['atr'].iloc[-1])
                                    
                                    signal_type = signal['side'].upper()
                                    if signal['side'] == 'long':
                                        suggested_stop_loss = current_price - (atr * config.STOP_LOSS_MULTIPLIER)
                                        suggested_take_profit = current_price + (atr * config.STOP_LOSS_MULTIPLIER * config.RISK_REWARD_RATIO)
                                    else:  # short
                                        suggested_stop_loss = current_price + (atr * config.STOP_LOSS_MULTIPLIER)
                                        suggested_take_profit = current_price - (atr * config.STOP_LOSS_MULTIPLIER * config.RISK_REWARD_RATIO)
                                    
                                    # 🚨 重要信號提醒
                                    logger.info(f"🚨🚨🚨 檢測到 {signal_type} 進場信號！🚨🚨🚨")
                                    logger.info(f"📊 建議進場價格: ${current_price:.4f}")
                                    logger.info(f"🛡️ 建議停損價格: ${suggested_stop_loss:.4f}")
                                    logger.info(f"🎯 建議停利價格: ${suggested_take_profit:.4f}")
                                    logger.info(f"📈 風險報酬比: 1:{config.RISK_REWARD_RATIO}")
                                    logger.info(f"📏 ATR 值: {atr:.4f}")
                                    
                                    print(f"🚨 【{signal_type} 進場信號】")
                                    print(f"⏰ 進場時間: {check_time_str}")
                                    print(f"💰 進場價格: ${current_price:.2f}")
                                    print(f"🛡️ 停損價格: ${suggested_stop_loss:.2f}")
                                    print(f"🎯 停利價格: ${suggested_take_profit:.2f}")
                                    print("=" * 50)
                                    
                                else:
                                    logger.info("📊 本次檢查無進場信號")
                                    print("❌ 無進場信號")
                                    
                                    # 記錄詳細的無信號原因到日誌
                                    logger.info("📋 信號分析詳情:")
                                    
                                    # 檢查1小時MACD狀態
                                    prev_1h_macd = self.data_1h['macd_histogram'].iloc[-3] if len(self.data_1h) > 2 else 0
                                    logger.info(f"   1H MACD: 當前={latest_1h_macd:.6f}, 前一根={prev_1h_macd:.6f}")
                                    
                                    if latest_1h_macd > 0 and prev_1h_macd <= 0:
                                        logger.info("   1H MACD 剛轉正，檢查4H確認...")
                                        if latest_4h_macd <= 0:
                                            logger.info("   ❌ 4H MACD 非正值，做多信號未確認")
                                    elif latest_1h_macd < 0 and prev_1h_macd >= 0:
                                        logger.info("   1H MACD 剛轉負，檢查4H確認...")
                                        if latest_4h_macd >= 0:
                                            logger.info("   ❌ 4H MACD 非負值，做空信號未確認")
                                    else:
                                        logger.info("   1H MACD 未出現轉向信號")
                                    
                                    # 4小時趋势分析（只记录到日志，不显示到控制台）
                                    if latest_4h_macd > 0:
                                        logger.info("   4H MACD > 0，整體偏多頭環境")
                                    elif latest_4h_macd < 0:
                                        logger.info("   4H MACD < 0，整體偏空頭環境")
                                    else:
                                        logger.info("   4H MACD 接近 0，趨勢不明確")
                                        
                                    if abs(latest_1h_macd) < 0.001:
                                        logger.info("   1H MACD 直方圖過小，信號強度不足")
                            else:
                                logger.warning(f"⚠️ 數據時間驗證失敗 (第{retry_count}次): {data_validation['reason']}")
                                print(f"⚠️ 數據時間驗證失敗 (第{retry_count}次): {data_validation['reason']}")
                                
                                if retry_count < max_retries:
                                    wait_time = 1  # 等待1秒後重試
                                    logger.info(f"⏳ 等待 {wait_time} 秒後重試...")
                                    print(f"⏳ 等待 {wait_time} 秒後重試...")
                                    time.sleep(wait_time)
                        else:
                            logger.warning(f"❌ 數據更新失敗 (第{retry_count}次)")
                            print(f"❌ 數據更新失敗 (第{retry_count}次)")
                            
                            if retry_count < max_retries:
                                wait_time = 1  # 等待1秒後重試
                                logger.info(f"⏳ 等待 {wait_time} 秒後重試...")
                                print(f"⏳ 等待 {wait_time} 秒後重試...")
                                time.sleep(wait_time)
                    
                    if not data_acquired:
                        logger.error(f"❌ 經過 {max_retries} 次嘗試仍無法獲得正確數據，跳過本次檢查")
                        print(f"❌ 經過 {max_retries} 次嘗試仍無法獲得正確數據，跳過本次檢查")
                    
                    # 記錄檢查完成
                    last_entry_check_hour = current_hour
                    check_end_time = datetime.now()
                    check_duration = (check_end_time - current_time).total_seconds()
                    
                    # 顯示統計信息
                    remaining_time = end_time - datetime.now()
                    remaining_hours = remaining_time.total_seconds() / 3600
                    next_check_time = current_time.replace(minute=0, second=1, microsecond=0) + timedelta(hours=1)
                    
                    logger.info(f"✅ 本次檢查完成，耗時 {check_duration:.1f} 秒")
                    logger.info(f"📈 信號統計: 已檢測到 {signal_count} 個信號")
                    logger.info(f"⏳ 剩餘監測時間: {remaining_hours:.1f} 小時")
                    logger.info(f"🕐 下次檢查時間: {next_check_time.strftime('%H:%M:%S')}")
                    
                    print(f"🕐 下次檢查: {next_check_time.strftime('%H:%M:%S')} (信號數: {signal_count})")
                    print("-" * 40)
                
                # 每1秒檢查一次時間，確保能準確捕捉到整點1秒
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("收到中斷信號，停止信號監測")
                print("⚠️ 收到中斷信號，停止信號監測")
                break
            except Exception as e:
                logger.error(f"信號監測錯誤: {e}")
                print(f"❌ 信號監測錯誤: {e}")
                time.sleep(60)  # 錯誤後等待1分鐘
        
        # 記錄監測結束
        logger.info("🏁 信號監測結束")
        logger.info(f"📊 監測總結: 運行 {duration_hours} 小時，檢測到 {signal_count} 個信號")
        
        return {
            'total_signals': signal_count,
            'monitoring_duration': duration_hours,
            'end_time': datetime.now().isoformat()
        }
    
    def _validate_data_timing(self, check_time: datetime) -> dict:
        """
        驗證數據時間是否正確
        
        Args:
            check_time: 檢查時間 (本地時間 UTC+8，比如10:00:01)
            
        Returns:
            驗證結果字典
        """
        try:
            # 獲取最新數據的時間戳（API返回的是UTC時間）
            latest_1h_timestamp = pd.to_datetime(self.data_1h.index[-1])
            latest_4h_timestamp = pd.to_datetime(self.data_4h.index[-1])
            
            # 統一處理時區問題 - 移除時區信息
            if latest_1h_timestamp.tz is not None:
                latest_1h_timestamp = latest_1h_timestamp.tz_localize(None)
            if latest_4h_timestamp.tz is not None:
                latest_4h_timestamp = latest_4h_timestamp.tz_localize(None)
            
            # 確保check_time也沒有時區信息
            if hasattr(check_time, 'tz') and check_time.tz is not None:
                check_time = check_time.replace(tzinfo=None)
            
            # 將本地時間（UTC+8）轉換為UTC時間進行比較
            utc_check_time = check_time - timedelta(hours=8)
            
            # ===== 1小時線邏輯 =====
            # 在11:00:01檢查時，API會返回11:00開盤的進行中K線
            # 但我們要用10:00的已完成K線來做交易判斷
            # 所以期望API返回的最新K線是當前小時（11:00）
            expected_1h_time_utc = utc_check_time.replace(minute=0, second=0, microsecond=0)
            
            # ===== 4小時線邏輯 =====
            # 在10:00:01檢查時，要看當前4小時週期（8-12點）的開盤時間
            # 計算當前所在的4小時週期起始點
            local_current_hour = check_time.hour
            current_4h_start_local = (local_current_hour // 4) * 4
            
            # 轉換為UTC時間的4小時週期起始點
            utc_4h_start_hour = (current_4h_start_local - 8) % 24
            if current_4h_start_local < 8:
                # 如果本地時間的4小時週期起始點在8點之前，需要看前一天
                expected_4h_time_utc = (utc_check_time - timedelta(days=1)).replace(
                    hour=utc_4h_start_hour, minute=0, second=0, microsecond=0)
            else:
                expected_4h_time_utc = utc_check_time.replace(
                    hour=utc_4h_start_hour, minute=0, second=0, microsecond=0)
            
            # 計算時間差（小時為單位）
            time_diff_1h_hours = (latest_1h_timestamp - expected_1h_time_utc).total_seconds() / 3600
            time_diff_4h_hours = (latest_4h_timestamp - expected_4h_time_utc).total_seconds() / 3600
            
            # 驗證邏輯：
            # 1小時線：容忍度2小時，如果差異超過2小時就需要重試
            # 4小時線：檢查是否有當前週期的數據
            is_1h_valid = abs(time_diff_1h_hours) < 2.0
            is_4h_valid = time_diff_4h_hours >= 0 and time_diff_4h_hours < 4.0  # 當前4小時週期內的數據
            
            # 格式化時間字符串（轉換為本地時間顯示）
            latest_1h_local = latest_1h_timestamp + timedelta(hours=8)  # UTC轉換為UTC+8
            latest_4h_local = latest_4h_timestamp + timedelta(hours=8)  # UTC轉換為UTC+8
            expected_1h_local = expected_1h_time_utc + timedelta(hours=8)  # UTC轉換為UTC+8
            expected_4h_local = expected_4h_time_utc + timedelta(hours=8)  # UTC轉換為UTC+8
            
            latest_1h_str = latest_1h_local.strftime('%m-%d %H:%M')
            latest_4h_str = latest_4h_local.strftime('%m-%d %H:%M')
            expected_1h_str = expected_1h_local.strftime('%m-%d %H:%M')
            expected_4h_str = expected_4h_local.strftime('%m-%d %H:%M')
            
            if is_1h_valid and is_4h_valid:
                return {
                    'valid': True,
                    'latest_1h_time': latest_1h_str,
                    'latest_4h_time': latest_4h_str,
                    'data_info': f"1H最新: {latest_1h_str}, 4H最新: {latest_4h_str}",
                    'reason': None
                }
            else:
                reason_parts = []
                if not is_1h_valid:
                    if abs(time_diff_1h_hours) >= 2.0:
                        reason_parts.append(f"1H數據延遲過大 (期望: {expected_1h_str}, 實際: {latest_1h_str}, 差異: {time_diff_1h_hours:+.1f}小時)")
                    else:
                        reason_parts.append(f"1H數據時間異常 (期望: {expected_1h_str}, 實際: {latest_1h_str}, 差異: {time_diff_1h_hours:+.1f}小時)")
                
                if not is_4h_valid:
                    if time_diff_4h_hours < 0:
                        reason_parts.append(f"4H數據未更新 (期望當前週期: {expected_4h_str}, 實際: {latest_4h_str}, 差異: {time_diff_4h_hours:+.1f}小時)")
                    elif time_diff_4h_hours >= 4.0:
                        reason_parts.append(f"4H數據過新 (期望當前週期: {expected_4h_str}, 實際: {latest_4h_str}, 差異: {time_diff_4h_hours:+.1f}小時)")
                    else:
                        reason_parts.append(f"4H數據異常 (期望當前週期: {expected_4h_str}, 實際: {latest_4h_str}, 差異: {time_diff_4h_hours:+.1f}小時)")
                
                return {
                    'valid': False,
                    'latest_1h_time': latest_1h_str,
                    'latest_4h_time': latest_4h_str,
                    'data_info': f"1H最新: {latest_1h_str}, 4H最新: {latest_4h_str}",
                    'reason': "; ".join(reason_parts)
                }
                
        except Exception as e:
            return {
                'valid': False,
                'latest_1h_time': 'N/A',
                'latest_4h_time': 'N/A',
                'data_info': 'N/A',
                'reason': f"數據時間驗證異常: {e}"
            }
    
    def get_performance_summary(self) -> dict:
        """
        獲取績效摘要
        
        Returns:
            績效統計字典
        """
        win_rate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        
        summary = {
            'total_trades': self.trade_count,
            'winning_trades': self.win_count,
            'losing_trades': self.trade_count - self.win_count,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'average_pnl': self.total_pnl / self.trade_count if self.trade_count > 0 else 0,
            'positions': [pos.to_dict() for pos in self.positions]
        }
        
        logger.info(f"策略績效摘要:")
        logger.info(f"總交易次數: {summary['total_trades']}")
        logger.info(f"勝率: {summary['win_rate']:.2f}%")
        logger.info(f"總損益: {summary['total_pnl']:.4f}")
        
        # 同時在控制台顯示績效摘要
        print(f"\n📊 策略績效摘要:")
        print(f"📈 總交易次數: {summary['total_trades']}")
        print(f"🎯 勝率: {summary['win_rate']:.2f}%")
        print(f"💰 總損益: ${summary['total_pnl']:+.4f}")
        print(f"💵 平均每筆損益: ${summary['average_pnl']:+.4f}")
        
        return summary
    
    def backtest(self, start_date: str, end_date: str) -> dict:
        """
        回測策略
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            
        Returns:
            回測結果
        """
        logger.info(f"開始回測 - 期間: {start_date} 到 {end_date}")
        
        # 這裡可以實現詳細的回測邏輯
        # 由於篇幅限制，這裡提供基本框架
        
        # 獲取歷史數據
        # 逐步模擬交易
        # 計算績效指標
        
        return self.get_performance_summary()


def main():
    """主程式入口"""
    try:
        # 建立策略實例（使用真實 Binance 數據）
        strategy = MacdTradingStrategy()
        
        # 設定運行時間
        print("🚀 MACD 信號監測系統啟動")
        print("📢 純提醒模式：只監測信號，不執行交易")
        print("⚡ 監測頻率：每小時整點檢查進場信號")
        print("🎲 檢測到信號時會提醒，手動下單後讓幣安自動執行")
        print("-" * 80)
        
        # 執行信號監測（預設 24 小時）
        results = strategy.run_strategy(duration_hours=24)
        
        print("\n=== 信號監測結束 ===")
        print(f"📊 總檢測信號數: {results['total_signals']}")
        print(f"⏰ 監測時長: {results['monitoring_duration']} 小時")
        print(f"🏁 結束時間: {results['end_time']}")
        
    except Exception as e:
        logger.error(f"主程式執行錯誤: {e}")
        print(f"❌ 程式執行錯誤: {e}")


def test_short_run():
    """測試短時間運行（10分鐘）"""
    try:
        print("🧪 測試模式 - 運行 10 分鐘...")
        strategy = MacdTradingStrategy()
        
        # 運行 10 分鐘進行測試
        results = strategy.run_strategy(duration_hours=0.167)  # 10分鐘
        
        print("\n=== 測試結果 ===")
        print(f"📊 檢測信號數: {results['total_signals']}")
        print(f"⏰ 測試時長: {results['monitoring_duration']} 小時")
        
    except Exception as e:
        logger.error(f"測試執行錯誤: {e}")
        print(f"❌ 測試執行錯誤: {e}")


if __name__ == "__main__":
    # 如果想要測試模式（10分鐘），取消下面這行的註解
    # test_short_run()
    
    # 正常運行模式（24小時）
    main() 