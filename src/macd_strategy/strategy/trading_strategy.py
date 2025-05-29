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

from ..core import config
from ..data.data_provider import DataProvider
from ..indicators.technical_indicators import TechnicalIndicators, SignalAnalyzer

# 設定日誌
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
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
        
        logger.info(f"MACD 交易策略初始化完成 - 交易對: {self.symbol}")
    
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
            
            # 使用信號分析器檢查做多信號
            long_signal = self.signal_analyzer.analyze_long_signal(data_1h, data_4h)
            if long_signal.get('signal', False):
                return 'BUY'
            
            # 檢查做空信號
            short_signal = self.signal_analyzer.analyze_short_signal(data_1h, data_4h)
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
            # 計算倉位大小
            position_size = config.POSITION_SIZE
            
            # 建立持倉
            position = Position(
                side=signal['side'],
                entry_price=signal['entry_price'],
                size=position_size,
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                timestamp=datetime.now()
            )
            
            self.current_position = position
            self.positions.append(position)
            
            logger.info(f"進場執行成功 - {signal['side'].upper()} "
                       f"價格: {signal['entry_price']:.4f} "
                       f"停損: {signal['stop_loss']:.4f} "
                       f"停利: {signal['take_profit']:.4f}")
            
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
    
    def run_strategy(self, duration_hours: int = 24) -> dict:
        """
        運行 MACD 交易策略（即時監控模式）
        - 每小時第5秒：檢查進場信號（基於上一小時完整數據）
        - 每5秒：檢查出場條件（基於即時價格）
        
        Args:
            duration_hours: 運行時長（小時）
            
        Returns:
            策略運行結果
        """
        entry_check_second = config.HIGH_FREQ_MODE["ENTRY_CHECK_SECOND"]
        exit_check_interval = config.HIGH_FREQ_MODE["EXIT_CHECK_INTERVAL"]
        use_realtime_price = config.HIGH_FREQ_MODE["USE_REALTIME_PRICE"]
        
        logger.info(f"開始運行 MACD 交易策略，預計運行 {duration_hours} 小時")
        logger.info(f"監測頻率：每小時第{entry_check_second}秒檢查進場，每{exit_check_interval}秒檢查出場")
        logger.info(f"價格模式：{'即時價格' if use_realtime_price else '收盤價格'}")
        print(f"🚀 啟動 MACD 交易策略，預計運行 {duration_hours} 小時")
        print(f"⚡ 監測模式：每小時第{entry_check_second}秒檢查進場，每{exit_check_interval}秒檢查出場")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        
        last_entry_check_hour = -1  # 記錄上次檢查進場信號的小時
        loop_count = 0  # 循環計數器
        
        while datetime.now() < end_time:
            try:
                current_time = datetime.now()
                current_hour = current_time.hour
                current_second = current_time.second
                loop_count += 1
                
                # 每小時第N秒檢查進場信號
                if (current_second == entry_check_second and 
                    current_hour != last_entry_check_hour and 
                    self.current_position is None):
                    
                    logger.info(f"⏰ {current_time.strftime('%H:%M:%S')} - 執行每小時進場信號檢查")
                    print(f"⏰ {current_time.strftime('%H:%M:%S')} - 執行每小時進場信號檢查")
                    
                    # 更新市場數據（獲取完整的上一小時數據）
                    logger.info("📡 開始更新市場數據（獲取完整上一小時數據）...")
                    print("📡 開始更新市場數據...")
                    
                    if self.update_market_data():
                        logger.info("✅ 市場數據更新成功")
                        
                        # 獲取當前價格信息
                        current_price = self.data_provider.get_current_price(self.symbol)
                        latest_1h_close = self.data_1h['close'].iloc[-1]
                        latest_4h_close = self.data_4h['close'].iloc[-1]
                        
                        # 獲取最新的 MACD 數據
                        latest_1h_macd = self.data_1h['macd_histogram'].iloc[-1]
                        latest_4h_macd = self.data_4h['macd_histogram'].iloc[-1]
                        
                        logger.info(f"💰 當前市場價格:")
                        logger.info(f"   即時價格: ${current_price:.4f}" if current_price else "   即時價格: 獲取失敗")
                        logger.info(f"   1H 收盤價: ${latest_1h_close:.4f}")
                        logger.info(f"   4H 收盤價: ${latest_4h_close:.4f}")
                        logger.info(f"📊 MACD 指標狀態:")
                        logger.info(f"   1H MACD 直方圖: {latest_1h_macd:.6f}")
                        logger.info(f"   4H MACD 直方圖: {latest_4h_macd:.6f}")
                        
                        print(f"💰 當前市場價格:")
                        print(f"   即時價格: ${current_price:.4f}" if current_price else "   即時價格: 獲取失敗")
                        print(f"   1H 收盤價: ${latest_1h_close:.4f}")
                        print(f"   4H 收盤價: ${latest_4h_close:.4f}")
                        print(f"📊 MACD 指標狀態:")
                        print(f"   1H MACD 直方圖: {latest_1h_macd:.6f}")
                        print(f"   4H MACD 直方圖: {latest_4h_macd:.6f}")
                        
                        # 檢查進場信號
                        logger.info("🔍 開始分析進場信號...")
                        print("🔍 開始分析進場信號...")
                        
                        signal = self.check_entry_signals()
                        if signal:
                            logger.info(f"🎯 檢測到進場信號: {signal['side'].upper()}")
                            logger.info(f"📊 進場價格: {signal['entry_price']:.4f}, 停損: {signal['stop_loss']:.4f}, 停利: {signal['take_profit']:.4f}")
                            
                            print(f"🎯 檢測到進場信號: {signal['side'].upper()}")
                            print(f"📊 進場價格: {signal['entry_price']:.4f}, 停損: {signal['stop_loss']:.4f}, 停利: {signal['take_profit']:.4f}")
                            
                            self.execute_entry(signal)
                        else:
                            logger.info("📊 無進場信號")
                            print("📊 無進場信號")
                            
                            # 提供更詳細的無信號原因
                            logger.info("📋 信號分析詳情:")
                            if latest_4h_macd > 0:
                                logger.info("   4H MACD > 0，可能的做多環境")
                                print("   4H MACD > 0，可能的做多環境")
                            elif latest_4h_macd < 0:
                                logger.info("   4H MACD < 0，可能的做空環境")
                                print("   4H MACD < 0，可能的做空環境")
                            else:
                                logger.info("   4H MACD 接近 0，趨勢不明確")
                                print("   4H MACD 接近 0，趨勢不明確")
                                
                            if abs(latest_1h_macd) < 0.001:
                                logger.info("   1H MACD 直方圖過小，信號不夠強烈")
                                print("   1H MACD 直方圖過小，信號不夠強烈")
                    else:
                        logger.warning("❌ 數據更新失敗，跳過本次進場檢查")
                        print("❌ 數據更新失敗，跳過本次進場檢查")
                    
                    last_entry_check_hour = current_hour
                
                # 每N秒檢查出場條件（如果有持倉）
                if self.current_position is not None:
                    exit_reason = self.check_exit_conditions(use_realtime_price=use_realtime_price)
                    if exit_reason:
                        logger.info(f"🚪 觸發出場條件: {exit_reason}")
                        print(f"🚪 觸發出場條件: {exit_reason}")
                        self.execute_exit(exit_reason)
                    elif loop_count % 12 == 0:  # 每分鐘輸出一次持倉狀態
                        current_price = self.data_provider.get_current_price(self.symbol)
                        if current_price:
                            unrealized_pnl = (current_price - self.current_position.entry_price) * self.current_position.size
                            if self.current_position.side == 'short':
                                unrealized_pnl = -unrealized_pnl
                            logger.info(f"💼 持倉狀態 - 方向: {self.current_position.side.upper()}, "
                                      f"當前價格: {current_price:.4f}, 未實現損益: {unrealized_pnl:.4f}")
                            print(f"💼 持倉狀態 - 方向: {self.current_position.side.upper()}, "
                                  f"當前價格: {current_price:.4f}, 未實現損益: {unrealized_pnl:+.4f}")
                
                # 每5分鐘顯示一次策略統計（60次循環 = 5分鐘）
                if loop_count % 60 == 0:
                    logger.info(f"📈 策略統計: 總交易 {self.trade_count} 次, 勝率 {(self.win_count/max(1,self.trade_count)*100):.1f}%, 總損益 ${self.total_pnl:+.4f}")
                    print(f"📈 策略統計: 總交易 {self.trade_count} 次, 勝率 {(self.win_count/max(1,self.trade_count)*100):.1f}%, 總損益 ${self.total_pnl:+.4f}")
                    
                    # 計算剩餘時間
                    remaining_time = end_time - datetime.now()
                    remaining_hours = remaining_time.total_seconds() / 3600
                    logger.info(f"⏳ 策略剩餘運行時間: {remaining_hours:.1f} 小時")
                    print(f"⏳ 策略剩餘運行時間: {remaining_hours:.1f} 小時")
                    print("-" * 60)
                
                # 等待指定秒數後下次檢查
                time.sleep(exit_check_interval)
                
            except KeyboardInterrupt:
                logger.info("收到中斷信號，停止策略運行")
                print("⚠️ 收到中斷信號，停止策略運行")
                break
            except Exception as e:
                logger.error(f"策略運行錯誤: {e}")
                print(f"❌ 策略運行錯誤: {e}")
                time.sleep(exit_check_interval)  # 錯誤後等待指定秒數
        
        # 如果還有持倉，強制平倉
        if self.current_position:
            logger.info("策略結束，執行強制平倉")
            print("🔚 策略結束，執行強制平倉")
            self.execute_exit("strategy_end")
        
        return self.get_performance_summary()
    
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
        print("🚀 MACD 交易策略啟動")
        print("⚡ 監測模式：每小時第5秒檢查進場，每5秒檢查出場條件")
        print("-" * 60)
        
        # 執行策略（預設 24 小時）
        results = strategy.run_strategy(duration_hours=24)
        
        print("\n=== 策略運行結束 ===")
        print(f"總交易次數: {results['total_trades']}")
        print(f"勝率: {results['win_rate']:.2f}%")
        print(f"總損益: ${results['total_pnl']:+.4f}")
        
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
        print(f"總交易次數: {results['total_trades']}")
        print(f"勝率: {results['win_rate']:.2f}%")
        print(f"總損益: ${results['total_pnl']:+.4f}")
        
    except Exception as e:
        logger.error(f"測試執行錯誤: {e}")
        print(f"❌ 測試執行錯誤: {e}")


if __name__ == "__main__":
    # 如果想要測試模式（10分鐘），取消下面這行的註解
    # test_short_run()
    
    # 正常運行模式（24小時）
    main() 