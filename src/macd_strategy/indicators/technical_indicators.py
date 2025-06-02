"""
技術指標計算模組
包含 MACD、ATR 等交易策略所需的技術指標
"""

import pandas as pd
import numpy as np
import ta
from typing import Tuple, Optional
import logging
from ..core import config
from pathlib import Path

# 設定模組專用logger，只輸出到日誌文件
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, config.LOG_LEVEL))

# 防止向根logger傳播，避免在控制台重複顯示
logger.propagate = False

# 確保logs目錄存在並設定文件handler
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 如果還沒有handler，添加文件handler
if not logger.handlers:
    file_handler = logging.FileHandler(
        config.BACKTEST_LOG_FILE, 
        mode='a',  # 追加模式
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)


class TechnicalIndicators:
    """技術指標計算器"""
    
    @staticmethod
    def calculate_macd(data: pd.DataFrame, 
                      fast: int = None, 
                      slow: int = None, 
                      signal: int = None) -> pd.DataFrame:
        """
        計算 MACD 指標
        
        Args:
            data: 包含 close 價格的 DataFrame
            fast: 快線週期 (None時使用config預設值)
            slow: 慢線週期 (None時使用config預設值)
            signal: 信號線週期 (None時使用config預設值)
            
        Returns:
            包含 MACD 指標的 DataFrame
        """
        try:
            # 使用config預設值
            if fast is None:
                fast = config.MACD_FAST
            if slow is None:
                slow = config.MACD_SLOW
            if signal is None:
                signal = config.MACD_SIGNAL
                
            df = data.copy()
            
            # 計算 MACD
            macd_line = ta.trend.MACD(close=df['close'], window_fast=fast, window_slow=slow, window_sign=signal)
            
            df['macd'] = macd_line.macd()
            df['macd_signal'] = macd_line.macd_signal()
            df['macd_histogram'] = macd_line.macd_diff()
            
            logger.debug(f"成功計算 MACD 指標，參數: fast={fast}, slow={slow}, signal={signal}")
            return df
            
        except Exception as e:
            logger.error(f"計算 MACD 指標失敗: {e}")
            return data
    
    @staticmethod
    def calculate_atr(data: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        計算 ATR (Average True Range) 指標
        
        Args:
            data: 包含 high, low, close 價格的 DataFrame
            period: ATR 計算週期 (None時使用config預設值)
            
        Returns:
            包含 ATR 指標的 DataFrame
        """
        try:
            # 使用config預設值
            if period is None:
                period = config.ATR_PERIOD
                
            df = data.copy()
            
            # 計算 ATR
            df['atr'] = ta.volatility.AverageTrueRange(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=period
            ).average_true_range()
            
            logger.debug(f"成功計算 ATR 指標，週期: {period}")
            return df
            
        except Exception as e:
            logger.error(f"計算 ATR 指標失敗: {e}")
            return data
    
    @staticmethod
    def check_macd_turn_positive(macd_hist: pd.Series, min_consecutive: int = None) -> bool:
        """
        檢查 MACD 直方圖是否出現轉正信號（第一根轉正後立即判斷）
        
        條件：
        1. 第1根 <= 0（前一段還在空方）
        2. 第0根 > 0（剛轉正）
        3. 轉正之前，必須連續出現 >= N 根負值直方圖
        
        Args:
            macd_hist: MACD 直方圖序列
            min_consecutive: 最少連續負值直方圖數量 (None時使用config預設值)
            
        Returns:
            是否符合轉正條件
        """
        try:
            # 使用config預設值
            if min_consecutive is None:
                min_consecutive = config.MIN_CONSECUTIVE_BARS
                
            if len(macd_hist) < min_consecutive + 2:
                return False
            
            # 獲取最近的值
            current = macd_hist.iloc[-1]  # 第0根（最新，剛轉正）
            prev_1 = macd_hist.iloc[-2]   # 第1根（前一根，應該 <= 0）
            
            # 檢查基本轉正條件：前一根 <= 0，當前根 > 0
            if not (prev_1 <= 0 and current > 0):
                return False
            
            # 檢查轉正之前是否有足夠的連續負值
            consecutive_negative = 0
            for i in range(2, len(macd_hist)):
                if macd_hist.iloc[-i] < 0:
                    consecutive_negative += 1
                else:
                    break
            
            result = consecutive_negative >= min_consecutive
            if result:
                logger.info(f"MACD 轉正信號確認：連續 {consecutive_negative} 根負值後轉正（第一根轉正立即進場）")
            
            return result
            
        except Exception as e:
            logger.error(f"檢查 MACD 轉正失敗: {e}")
            return False
    
    @staticmethod
    def check_macd_turn_negative(macd_hist: pd.Series, min_consecutive: int = None) -> bool:
        """
        檢查 MACD 直方圖是否出現轉負信號（第一根轉負後立即判斷）
        
        條件：
        1. 第1根 >= 0（前一段還在多方）
        2. 第0根 < 0（剛轉負）
        3. 轉負之前，必須連續出現 >= N 根正值直方圖
        
        Args:
            macd_hist: MACD 直方圖序列
            min_consecutive: 最少連續正值直方圖數量 (None時使用config預設值)
            
        Returns:
            是否符合轉負條件
        """
        try:
            # 使用config預設值
            if min_consecutive is None:
                min_consecutive = config.MIN_CONSECUTIVE_BARS
                
            if len(macd_hist) < min_consecutive + 2:
                return False
            
            # 獲取最近的值
            current = macd_hist.iloc[-1]  # 第0根（最新，剛轉負）
            prev_1 = macd_hist.iloc[-2]   # 第1根（前一根，應該 >= 0）
            
            # 檢查基本轉負條件：前一根 >= 0，當前根 < 0
            if not (prev_1 >= 0 and current < 0):
                return False
            
            # 檢查轉負之前是否有足夠的連續正值
            consecutive_positive = 0
            for i in range(2, len(macd_hist)):
                if macd_hist.iloc[-i] > 0:
                    consecutive_positive += 1
                else:
                    break
            
            result = consecutive_positive >= min_consecutive
            if result:
                logger.info(f"MACD 轉負信號確認：連續 {consecutive_positive} 根正值後轉負（第一根轉負立即進場）")
            
            return result
            
        except Exception as e:
            logger.error(f"檢查 MACD 轉負失敗: {e}")
            return False
    
    @staticmethod
    def calculate_stop_loss_take_profit(entry_price: float, atr: float, 
                                      stop_multiplier: float = None, 
                                      risk_reward: float = None,
                                      is_long: bool = True) -> Tuple[float, float]:
        """
        計算動態停損和停利價位
        
        Args:
            entry_price: 進場價格
            atr: ATR 值
            stop_multiplier: 停損倍數 (None時使用config預設值)
            risk_reward: 風報比 (None時使用config預設值)
            is_long: 是否為多單
            
        Returns:
            (停損價位, 停利價位)
        """
        try:
            # 使用config預設值
            if stop_multiplier is None:
                stop_multiplier = config.STOP_LOSS_MULTIPLIER
            if risk_reward is None:
                risk_reward = config.RISK_REWARD_RATIO
                
            stop_distance = atr * stop_multiplier
            profit_distance = stop_distance * risk_reward
            
            if is_long:
                stop_loss = entry_price - stop_distance
                take_profit = entry_price + profit_distance
            else:
                stop_loss = entry_price + stop_distance
                take_profit = entry_price - profit_distance
            
            logger.debug(f"計算停損停利 - 進場: {entry_price:.4f}, "
                        f"停損: {stop_loss:.4f}, 停利: {take_profit:.4f}")
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"計算停損停利失敗: {e}")
            return entry_price, entry_price


class SignalAnalyzer:
    """交易信號分析器"""
    
    def __init__(self, min_consecutive_bars: int = None):
        """
        初始化信號分析器
        
        Args:
            min_consecutive_bars: 最少連續直方圖數量 (None時使用config預設值)
        """
        if min_consecutive_bars is None:
            min_consecutive_bars = config.MIN_CONSECUTIVE_BARS
        self.min_consecutive_bars = min_consecutive_bars
    
    def analyze_long_signal(self, data_4h: pd.DataFrame, data_1h: pd.DataFrame) -> dict:
        """
        分析做多信號
        
        策略順序：
        1. 檢查當下的1小時K線是否為第一根轉正（當前正，前一根負）
        2. 檢查轉正之前的負值是否超過4根
        3. 檢查當下的4小時MACD直方圖是否也是正值
        
        Args:
            data_4h: 4小時數據（包含 MACD 指標）
            data_1h: 1小時數據（包含 MACD 指標）
            
        Returns:
            信號分析結果
        """
        try:
            result = {
                'signal': False,
                'conditions': {},
                'entry_price': None,
                'stop_loss': None,
                'take_profit': None,
                'atr': None,
                'details': {}
            }
            
            if len(data_1h) < self.min_consecutive_bars + 2:
                result['details']['error'] = '數據不足'
                return result
            
            # 第一步：檢查當下的1小時K線是否為第一根轉正
            current_1h = data_1h['macd_histogram'].iloc[-1]  # 當前根（如8:00~9:00）
            prev_1h = data_1h['macd_histogram'].iloc[-2]     # 前一根（如7:00~8:00）
            
            is_first_positive = current_1h > 0 and prev_1h <= 0
            result['conditions']['step1_first_positive'] = is_first_positive
            result['details']['current_1h_macd'] = current_1h
            result['details']['prev_1h_macd'] = prev_1h
            
            if not is_first_positive:
                result['details']['stop_reason'] = '不是第一根轉正'
                return result
            
            # 第二步：檢查轉正之前的負值是否超過4根
            consecutive_negative = 0
            for i in range(2, min(len(data_1h), 20)):  # 檢查前18根，避免無限回溯
                if data_1h['macd_histogram'].iloc[-i] < 0:
                    consecutive_negative += 1
                else:
                    break
            
            enough_negative = consecutive_negative >= self.min_consecutive_bars
            result['conditions']['step2_enough_negative'] = enough_negative
            result['details']['consecutive_negative_count'] = consecutive_negative
            
            if not enough_negative:
                result['details']['stop_reason'] = f'前段負值只有{consecutive_negative}根，需要>={self.min_consecutive_bars}根'
                return result
            
            # 第三步：檢查當下的4小時MACD直方圖是否也是正值
            current_4h = data_4h['macd_histogram'].iloc[-1]
            is_4h_positive = current_4h > 0
            result['conditions']['step3_4h_positive'] = is_4h_positive
            result['details']['current_4h_macd'] = current_4h
            
            if not is_4h_positive:
                result['details']['stop_reason'] = f'4小時MACD直方圖為負值: {current_4h:.6f}'
                return result
            
            # 所有條件滿足，確認做多信號
            result['signal'] = True
            result['atr'] = data_1h['atr'].iloc[-1]
            result['details']['signal_confirmed'] = '所有條件滿足'
            
            logger.info(f"做多信號確認！1h轉正(前{consecutive_negative}根負值) + 4h正值({current_4h:.6f})")
            
            return result
            
        except Exception as e:
            logger.error(f"分析做多信號失敗: {e}")
            return {'signal': False, 'conditions': {}, 'details': {'error': str(e)}}
    
    def analyze_short_signal(self, data_4h: pd.DataFrame, data_1h: pd.DataFrame) -> dict:
        """
        分析做空信號
        
        策略順序：
        1. 檢查當下的1小時K線是否為第一根轉負（當前負，前一根正）
        2. 檢查轉負之前的正值是否超過4根
        3. 檢查當下的4小時MACD直方圖是否也是負值
        
        Args:
            data_4h: 4小時數據（包含 MACD 指標）
            data_1h: 1小時數據（包含 MACD 指標）
            
        Returns:
            信號分析結果
        """
        try:
            result = {
                'signal': False,
                'conditions': {},
                'entry_price': None,
                'stop_loss': None,
                'take_profit': None,
                'atr': None,
                'details': {}
            }
            
            if len(data_1h) < self.min_consecutive_bars + 2:
                result['details']['error'] = '數據不足'
                return result
            
            # 第一步：檢查當下的1小時K線是否為第一根轉負
            current_1h = data_1h['macd_histogram'].iloc[-1]  # 當前根（如8:00~9:00）
            prev_1h = data_1h['macd_histogram'].iloc[-2]     # 前一根（如7:00~8:00）
            
            is_first_negative = current_1h < 0 and prev_1h >= 0
            result['conditions']['step1_first_negative'] = is_first_negative
            result['details']['current_1h_macd'] = current_1h
            result['details']['prev_1h_macd'] = prev_1h
            
            if not is_first_negative:
                result['details']['stop_reason'] = '不是第一根轉負'
                return result
            
            # 第二步：檢查轉負之前的正值是否超過4根
            consecutive_positive = 0
            for i in range(2, min(len(data_1h), 20)):  # 檢查前18根，避免無限回溯
                if data_1h['macd_histogram'].iloc[-i] > 0:
                    consecutive_positive += 1
                else:
                    break
            
            enough_positive = consecutive_positive >= self.min_consecutive_bars
            result['conditions']['step2_enough_positive'] = enough_positive
            result['details']['consecutive_positive_count'] = consecutive_positive
            
            if not enough_positive:
                result['details']['stop_reason'] = f'前段正值只有{consecutive_positive}根，需要>={self.min_consecutive_bars}根'
                return result
            
            # 第三步：檢查當下的4小時MACD直方圖是否也是負值
            current_4h = data_4h['macd_histogram'].iloc[-1]
            is_4h_negative = current_4h < 0
            result['conditions']['step3_4h_negative'] = is_4h_negative
            result['details']['current_4h_macd'] = current_4h
            
            if not is_4h_negative:
                result['details']['stop_reason'] = f'4小時MACD直方圖為正值: {current_4h:.6f}'
                return result
            
            # 所有條件滿足，確認做空信號
            result['signal'] = True
            result['atr'] = data_1h['atr'].iloc[-1]
            result['details']['signal_confirmed'] = '所有條件滿足'
            
            logger.info(f"做空信號確認！1h轉負(前{consecutive_positive}根正值) + 4h負值({current_4h:.6f})")
            
            return result
            
        except Exception as e:
            logger.error(f"分析做空信號失敗: {e}")
            return {'signal': False, 'conditions': {}, 'details': {'error': str(e)}} 