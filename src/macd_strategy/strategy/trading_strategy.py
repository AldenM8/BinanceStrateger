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
from ..trading.trade_executor import TradeExecutor

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
        self.trade_executor = TradeExecutor()  # 添加交易執行器
        
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
                self.symbol, "4h", required_4h
            )
            if data_4h_raw is None:
                logger.error("無法獲取 4小時數據")
                return False
            
            # 獲取 1小時數據
            data_1h_raw = self.data_provider.get_ohlcv_data(
                self.symbol, "1h", required_1h
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
    
    def run_strategy(self, duration_hours: float = None, auto_trade: bool = True) -> dict:
        """
        運行 MACD 交易策略（信號監測模式）
        - 每小時整點：開始檢查進場信號，持續重試直到獲得正確時間的數據
        - 支援自動交易模式：檢測到信號後自動執行交易
        
        Args:
            duration_hours: 運行時長（小時）
                         - None 或 負數：無限運行
                         - 正數：運行指定小時數
            auto_trade: 是否啟用自動交易
                      - True: 檢測到信號後自動執行交易
                      - False: 純提醒模式，不執行交易
            
        Returns:
            策略運行結果
        """
        
        # 判斷是否無限運行
        infinite_mode = duration_hours is None or duration_hours <= 0
        
        if infinite_mode:
            logger.info("開始運行 MACD 信號監測 - 無限模式")
            print(f"🚀 啟動 MACD 信號監測 - ♾️ 無限運行模式")
            print(f"💡 提示：按 Ctrl+C 可以停止監測")
        else:
            logger.info(f"開始運行 MACD 信號監測，預計運行 {duration_hours} 小時")
            print(f"🚀 啟動 MACD 信號監測，預計運行 {duration_hours} 小時")
        
        logger.info(f"監測頻率：每小時整點檢查進場信號，持續重試直到獲得正確數據")
        if auto_trade:
            logger.info(f"模式：自動交易模式 - 檢測到信號後自動執行交易")
            print(f"⚡ 監測模式：每小時整點檢查進場信號")
            print(f"🤖 自動交易模式：檢測到信號後自動執行交易")
        else:
            logger.info(f"模式：純提醒模式 - 不執行實際交易")
            print(f"⚡ 監測模式：每小時整點檢查進場信號")
            print(f"📢 純提醒模式：檢測到信號時會提醒，手動下單後讓幣安自動執行")
        print(f"🎯 交易對：{self.symbol}")
        print("-" * 80)
        
        start_time = datetime.now()
        if not infinite_mode:
            end_time = start_time + timedelta(hours=duration_hours)
        
        last_entry_check_hour = -1  # 記錄上次檢查進場信號的小時
        signal_count = 0  # 信號計數器
        
        # 主監測循環
        while True:
            try:
                current_time = datetime.now()
                
                # 檢查是否超過運行時間（僅在非無限模式）
                if not infinite_mode and current_time >= end_time:
                    break
                
                current_hour = current_time.hour
                current_minute = current_time.minute
                
                # 每小時1秒時檢查進場信號
                current_second = current_time.second
                if (current_minute == 0 and current_second == 1 and current_hour != last_entry_check_hour):
                    # 記錄檢查開始
                    check_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"\n{'='*80}")
                    print(f"🕐 時間: {check_time_str} | 小時信號檢查 #{current_hour}")
                    print(f"{'='*80}")
                    logger.info(f"\n{'='*80}")
                    logger.info(f"⏰ {check_time_str} - 開始執行每小時信號檢查")
                    logger.info(f"{'='*80}")
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
                                    
                                    # 詳細計算過程記錄到log
                                    logger.info(f"🚨🚨🚨 檢測到 {signal_type} 進場信號！🚨🚨🚨")
                                    logger.info(f"📊 信號詳細計算過程:")
                                    logger.info(f"   基礎數據:")
                                    logger.info(f"   - 當前價格: ${current_price:.4f}")
                                    logger.info(f"   - ATR 值: {atr:.4f}")
                                    logger.info(f"   - 停損倍數: {config.STOP_LOSS_MULTIPLIER}")
                                    logger.info(f"   - 風險報酬比: 1:{config.RISK_REWARD_RATIO}")
                                    logger.info(f"   - 倉位大小: {config.POSITION_SIZE * 100}%")
                                    
                                    if signal['side'] == 'long':
                                        stop_loss_distance = atr * config.STOP_LOSS_MULTIPLIER
                                        take_profit_distance = stop_loss_distance * config.RISK_REWARD_RATIO
                                        suggested_stop_loss = current_price - stop_loss_distance
                                        suggested_take_profit = current_price + take_profit_distance
                                        
                                        logger.info(f"   做多計算:")
                                        logger.info(f"   - 停損距離 = ATR × 停損倍數 = {atr:.4f} × {config.STOP_LOSS_MULTIPLIER} = {stop_loss_distance:.4f}")
                                        logger.info(f"   - 停利距離 = 停損距離 × 風報比 = {stop_loss_distance:.4f} × {config.RISK_REWARD_RATIO} = {take_profit_distance:.4f}")
                                        logger.info(f"   - 停損價格 = 進場價 - 停損距離 = {current_price:.4f} - {stop_loss_distance:.4f} = {suggested_stop_loss:.4f}")
                                        logger.info(f"   - 停利價格 = 進場價 + 停利距離 = {current_price:.4f} + {take_profit_distance:.4f} = {suggested_take_profit:.4f}")
                                    else:  # short
                                        stop_loss_distance = atr * config.STOP_LOSS_MULTIPLIER
                                        take_profit_distance = stop_loss_distance * config.RISK_REWARD_RATIO
                                        suggested_stop_loss = current_price + stop_loss_distance
                                        suggested_take_profit = current_price - take_profit_distance
                                        
                                        logger.info(f"   做空計算:")
                                        logger.info(f"   - 停損距離 = ATR × 停損倍數 = {atr:.4f} × {config.STOP_LOSS_MULTIPLIER} = {stop_loss_distance:.4f}")
                                        logger.info(f"   - 停利距離 = 停損距離 × 風報比 = {stop_loss_distance:.4f} × {config.RISK_REWARD_RATIO} = {take_profit_distance:.4f}")
                                        logger.info(f"   - 停損價格 = 進場價 + 停損距離 = {current_price:.4f} + {stop_loss_distance:.4f} = {suggested_stop_loss:.4f}")
                                        logger.info(f"   - 停利價格 = 進場價 - 停利距離 = {current_price:.4f} - {take_profit_distance:.4f} = {suggested_take_profit:.4f}")
                                    
                                    # 計算潛在盈虧
                                    risk_amount = abs(current_price - suggested_stop_loss)
                                    reward_amount = abs(suggested_take_profit - current_price)
                                    actual_risk_reward = reward_amount / risk_amount if risk_amount > 0 else 0
                                    
                                    logger.info(f"   風險管理:")
                                    logger.info(f"   - 風險金額: ${risk_amount:.4f}")
                                    logger.info(f"   - 報酬金額: ${reward_amount:.4f}")
                                    logger.info(f"   - 實際風報比: 1:{actual_risk_reward:.2f}")
                                    
                                    # 簡潔的控制台輸出
                                    print(f"🚨 【{signal_type} 信號】 ${current_price:.2f}")
                                    print(f"🛡️ 停損: ${suggested_stop_loss:.2f} | 🎯 停利: ${suggested_take_profit:.2f} | 📊 風報比: 1:{actual_risk_reward:.1f}")
                                    print("=" * 60)
                                    
                                    # 如果檢測到做多信號
                                    if long_analysis['signal']:
                                        logger.info("✅ 檢測到做多信號")
                                        print("✅ 檢測到做多信號")
                                        signal_count += 1
                                        
                                        if auto_trade:
                                            try:
                                                # 計算交易數量
                                                current_price = self.trade_executor.get_current_price()
                                                quantity = self.calculate_position_size(current_price)
                                                
                                                # 計算止盈止損價格
                                                stop_loss = current_price * (1 - config.STOP_LOSS_PERCENTAGE)
                                                take_profit = current_price * (1 + config.TAKE_PROFIT_PERCENTAGE)
                                                
                                                # 執行 OTOCO 訂單
                                                self.trade_executor.place_otoco_order(
                                                    side='BUY',
                                                    quantity=quantity,
                                                    entry_price=current_price,
                                                    stop_loss=stop_loss,
                                                    take_profit=take_profit
                                                )
                                                logger.info(f"已執行做多交易 - 數量: {quantity}, 價格: {current_price}")
                                                print(f"🤖 已執行做多交易 - 數量: {quantity}, 價格: {current_price}")
                                            except Exception as e:
                                                logger.error(f"執行做多交易失敗: {e}")
                                                print(f"❌ 執行做多交易失敗: {e}")
                                    
                                    # 如果檢測到做空信號
                                    if short_analysis['signal']:
                                        logger.info("✅ 檢測到做空信號")
                                        print("✅ 檢測到做空信號")
                                        signal_count += 1
                                        
                                        if auto_trade:
                                            try:
                                                # 計算交易數量
                                                current_price = self.trade_executor.get_current_price()
                                                quantity = self.calculate_position_size(current_price)
                                                
                                                # 計算止盈止損價格
                                                stop_loss = current_price * (1 + config.STOP_LOSS_PERCENTAGE)
                                                take_profit = current_price * (1 - config.TAKE_PROFIT_PERCENTAGE)
                                                
                                                # 執行 OTOCO 訂單
                                                self.trade_executor.place_otoco_order(
                                                    side='SELL',
                                                    quantity=quantity,
                                                    entry_price=current_price,
                                                    stop_loss=stop_loss,
                                                    take_profit=take_profit
                                                )
                                                logger.info(f"已執行做空交易 - 數量: {quantity}, 價格: {current_price}")
                                                print(f"🤖 已執行做空交易 - 數量: {quantity}, 價格: {current_price}")
                                            except Exception as e:
                                                logger.error(f"執行做空交易失敗: {e}")
                                                print(f"❌ 執行做空交易失敗: {e}")
                                    
                                else:
                                    logger.info("📊 本次檢查無進場信號")
                                    
                                    # 獲取詳細的信號分析結果 - 詳細分析記錄到log
                                    long_analysis = self.signal_analyzer.analyze_long_signal(self.data_4h, self.data_1h)
                                    short_analysis = self.signal_analyzer.analyze_short_signal(self.data_4h, self.data_1h)
                                    
                                    # 詳細分析記錄到日誌
                                    logger.info("📋 詳細信號分析:")
                                    
                                    # 分析做多信號失敗原因
                                    if 'details' in long_analysis and 'stop_reason' in long_analysis['details']:
                                        logger.info(f"   做多信號: {long_analysis['details']['stop_reason']}")
                                        
                                        # 詳細條件檢查記錄到log
                                        if 'conditions' in long_analysis:
                                            for condition, result in long_analysis['conditions'].items():
                                                status = "✅" if result else "❌"
                                                if condition == 'step1_first_positive':
                                                    desc = "1H MACD剛轉正"
                                                elif condition == 'step2_enough_negative':
                                                    desc = "前段負值足夠"
                                                elif condition == 'step3_4h_positive':
                                                    desc = "4H MACD為正"
                                                else:
                                                    desc = condition
                                                logger.info(f"      {status} {desc}: {result}")
                                        
                                        # 連續負值統計記錄到log
                                        if 'consecutive_negative_count' in long_analysis['details']:
                                            count = long_analysis['details']['consecutive_negative_count']
                                            logger.info(f"      前段連續負值: {count}/{config.MIN_CONSECUTIVE_BARS}根")
                                    
                                    # 分析做空信號失敗原因
                                    if 'details' in short_analysis and 'stop_reason' in short_analysis['details']:
                                        logger.info(f"   做空信號: {short_analysis['details']['stop_reason']}")
                                        
                                        # 詳細條件檢查記錄到log
                                        if 'conditions' in short_analysis:
                                            for condition, result in short_analysis['conditions'].items():
                                                status = "✅" if result else "❌"
                                                if condition == 'step1_first_negative':
                                                    desc = "1H MACD剛轉負"
                                                elif condition == 'step2_enough_positive':
                                                    desc = "前段正值足夠"
                                                elif condition == 'step3_4h_negative':
                                                    desc = "4H MACD為負"
                                                else:
                                                    desc = condition
                                                logger.info(f"      {status} {desc}: {result}")
                                        
                                        # 連續正值統計記錄到log
                                        if 'consecutive_positive_count' in short_analysis['details']:
                                            count = short_analysis['details']['consecutive_positive_count']
                                            logger.info(f"      前段連續正值: {count}/{config.MIN_CONSECUTIVE_BARS}根")
                                    
                                    # 通用MACD狀態分析記錄到log
                                    prev_1h_macd = self.data_1h['macd_histogram'].iloc[-3] if len(self.data_1h) > 2 else 0
                                    logger.info(f"   1H MACD: 當前={latest_1h_macd:.6f}, 前一根={prev_1h_macd:.6f}")
                                    
                                    # 4小時趨勢分析
                                    if latest_4h_macd > 0:
                                        trend_desc = "多頭環境"
                                        trend_emoji = "📈"
                                        logger.info(f"   4H MACD > 0，整體偏多頭環境")
                                    elif latest_4h_macd < 0:
                                        trend_desc = "空頭環境"
                                        trend_emoji = "📉"
                                        logger.info(f"   4H MACD < 0，整體偏空頭環境")
                                    else:
                                        trend_desc = "趨勢不明"
                                        trend_emoji = "➡️"
                                        logger.info(f"   4H MACD 接近 0，趨勢不明確")
                                        
                                    if abs(latest_1h_macd) < 0.001:
                                        logger.info("   1H MACD 直方圖過小，信號強度不足")
                                    
                                    # 簡潔的控制台輸出
                                    print(f"❌ 無信號 | {trend_emoji} {trend_desc} | 1H: {latest_1h_macd:.3f} | 4H: {latest_4h_macd:.1f}")
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
                    next_check_time = current_time.replace(minute=0, second=1, microsecond=0) + timedelta(hours=1)
                    total_runtime = (datetime.now() - start_time).total_seconds() / 3600
                    
                    logger.info(f"✅ 本次檢查完成，耗時 {check_duration:.1f} 秒")
                    logger.info(f"📈 信號統計: 已檢測到 {signal_count} 個信號")
                    
                    if infinite_mode:
                        logger.info(f"⏰ 已運行時間: {total_runtime:.1f} 小時")
                        logger.info(f"♾️ 無限監測模式 - 持續運行中")
                        print(f"🕐 下次檢查: {next_check_time.strftime('%H:%M:%S')} (信號數: {signal_count}, 已運行: {total_runtime:.1f}h)")
                    else:
                        remaining_time = end_time - datetime.now()
                        remaining_hours = remaining_time.total_seconds() / 3600
                        logger.info(f"⏳ 剩餘監測時間: {remaining_hours:.1f} 小時")
                        print(f"🕐 下次檢查: {next_check_time.strftime('%H:%M:%S')} (信號數: {signal_count}, 剩餘: {remaining_hours:.1f}h)")
                    
                    logger.info(f"🕐 下次檢查時間: {next_check_time.strftime('%H:%M:%S')}")
                    print("✅ 本次檢查完成")
                
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
        end_time = datetime.now()
        total_runtime = (end_time - start_time).total_seconds() / 3600
        
        logger.info("🏁 信號監測結束")
        if infinite_mode:
            logger.info(f"📊 監測總結: 無限模式運行了 {total_runtime:.1f} 小時，檢測到 {signal_count} 個信號")
            print(f"🏁 監測結束：運行了 {total_runtime:.1f} 小時，檢測到 {signal_count} 個信號")
        else:
            logger.info(f"📊 監測總結: 運行 {duration_hours} 小時，檢測到 {signal_count} 個信號")
            print(f"🏁 監測結束：運行 {duration_hours} 小時，檢測到 {signal_count} 個信號")
        
        return {
            'total_signals': signal_count,
            'monitoring_duration': total_runtime,
            'planned_duration': duration_hours,
            'infinite_mode': infinite_mode,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
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
            
            # ===== 4小時線邏輯修正 =====
            # 4小時線開盤時間: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 (UTC)
            # 對應台灣時間: 08:00, 12:00, 16:00, 20:00, 00:00, 04:00
            utc_hour = utc_check_time.hour
            current_4h_start_utc = (utc_hour // 4) * 4
            expected_4h_time_utc = utc_check_time.replace(
                hour=current_4h_start_utc, minute=0, second=0, microsecond=0
            )
            
            # 計算時間差（小時為單位）
            time_diff_1h_hours = (latest_1h_timestamp - expected_1h_time_utc).total_seconds() / 3600
            time_diff_4h_hours = (latest_4h_timestamp - expected_4h_time_utc).total_seconds() / 3600
            
            # 驗證邏輯：
            # 1小時線：容忍度2小時，如果差異超過2小時就需要重試
            # 4小時線：檢查是否有當前週期的數據（0-4小時內）
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
        
        # 設定運行時間和交易模式
        print("🚀 MACD 信號監測系統啟動")
        print("請選擇運行模式：")
        print("1. 自動交易模式 - 檢測到信號後自動執行交易")
        print("2. 純提醒模式 - 只監測信號，不執行交易")
        mode = input("請輸入選項 (1-2): ").strip()
        
        auto_trade = mode == '1'
        
        if auto_trade:
            print("🤖 已選擇自動交易模式")
        else:
            print("📢 已選擇純提醒模式")
        
        print("⚡ 監測頻率：每小時整點檢查進場信號")
        print("🎲 交易對：", strategy.symbol)
        print("♾️ 持續運行模式 - 按 Ctrl+C 停止")
        print("-" * 80)
        
        # 執行信號監測（無限運行模式）
        results = strategy.run_strategy(duration_hours=None, auto_trade=auto_trade)
        
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