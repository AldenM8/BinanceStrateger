"""
MACD 策略回測引擎
重構自 real_data_backtest.py，採用更模組化的設計
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import sys
import os
import logging
from pathlib import Path

# 處理相對導入問題
try:
    from ..data.data_provider import get_binance_klines
    from ..indicators.technical_indicators import TechnicalIndicators, SignalAnalyzer
    from ..strategy.trading_strategy import MacdTradingStrategy
    from ..core import config
except ImportError:
    # 如果相對導入失敗，嘗試添加路徑並使用絕對導入
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    grandparent_dir = os.path.dirname(parent_dir)
    root_dir = os.path.dirname(grandparent_dir)
    
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    
    try:
        from src.macd_strategy.data.data_provider import get_binance_klines
        from src.macd_strategy.indicators.technical_indicators import TechnicalIndicators, SignalAnalyzer
        from src.macd_strategy.strategy.trading_strategy import MacdTradingStrategy
        from src.macd_strategy.core import config
    except ImportError as e:
        print(f"❌ 無法導入必要模組: {e}")
        print("請確保從專案根目錄執行程式，或使用 main.py 作為入口點")
        sys.exit(1)

# 設定台灣時區 (UTC+8)
TAIWAN_TZ = timezone(timedelta(hours=8))


def setup_backtest_logging():
    """設定回測專用日誌"""
    try:
        from ..core import config
    except ImportError:
        # 如果相對導入失敗，使用絕對導入
        from src.macd_strategy.core import config
    
    # 確保logs目錄存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 創建帶時間戳的日誌檔名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"backtest_{timestamp}.log"
    log_path = log_dir / log_filename
    
    # 創建回測日誌記錄器
    logger = logging.getLogger('backtest')
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # 避免重複添加handler
    if not logger.handlers:
        # 文件handler
        file_handler = logging.FileHandler(
            log_path, 
            mode='w',  # 每次回測都重新開始
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
        
        # 格式設定（只為文件handler設定格式）
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 只添加文件handler，不要控制台handler
        logger.addHandler(file_handler)
        
        # 防止向父logger傳播，避免重複輸出
        logger.propagate = False
    
    return logger


class BacktestEngine:
    """MACD 策略回測引擎"""
    
    def __init__(self, initial_capital: float = 10000.0):
        """
        初始化回測引擎
        
        Args:
            initial_capital: 初始資金
        """
        self.initial_capital = initial_capital
        self.signal_analyzer = SignalAnalyzer(min_consecutive_bars=config.MIN_CONSECUTIVE_BARS)
        self.logger = setup_backtest_logging()
        
    def format_taiwan_time(self, timestamp) -> str:
        """將時間戳轉換為台灣時間字串"""
        if pd.isna(timestamp):
            return "N/A"
        
        # 確保是 datetime 對象
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        
        # 轉換為台灣時間
        if timestamp.tz is None:
            # 假設是 UTC 時間
            taiwan_time = timestamp.replace(tzinfo=timezone.utc).astimezone(TAIWAN_TZ)
        else:
            taiwan_time = timestamp.astimezone(TAIWAN_TZ)
        
        return taiwan_time.strftime('%m-%d %H:%M')
    
    def execute_backtest(self, data_1h: pd.DataFrame, data_4h: pd.DataFrame, 
                        data_1h_full: Optional[pd.DataFrame] = None, 
                        data_4h_full: Optional[pd.DataFrame] = None,
                        symbol: str = None) -> Dict:
        """
        執行回測策略
        
        Args:
            data_1h: 1小時數據（實際回測期間）
            data_4h: 4小時數據（實際回測期間）
            data_1h_full: 完整1小時數據（含預熱期）
            data_4h_full: 完整4小時數據（含預熱期）
            symbol: 交易對符號（None 表示使用 config 預設值）
            
        Returns:
            回測結果字典
        """
        # 處理交易對符號，提取基礎幣種名稱
        if symbol is None:
            symbol = config.SYMBOL
        
        # 提取基礎幣種名稱（移除 USDT 後綴）
        base_currency = symbol.replace('USDT', '') if symbol.endswith('USDT') else symbol.split('/')[0]
        
        # 初始化回測變數
        capital = self.initial_capital
        position = None  # 'long', 'short', None
        position_size = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        entry_time = None
        margin_used = 0  # 占用的保證金
        notional_value = 0  # 名義價值
        trades = []
        
        # 待進場信號
        pending_signal = None  # {'type': 'long'/'short', 'atr': value, 'time': time}
        
        print("🔄 開始模擬交易...")
        
        # 使用適當的數據源進行分析（優先使用完整數據）
        analysis_data_1h = data_1h_full if data_1h_full is not None else data_1h
        analysis_data_4h = data_4h_full if data_4h_full is not None else data_4h
        
        # 遍歷交易數據
        for i, (current_time, row) in enumerate(data_1h.iterrows()):
            current_price = row['close']  # 當前K線收盤價
            current_high = row['high']    # 當前K線最高價
            current_low = row['low']      # 當前K線最低價
            current_open = row['open']    # 當前K線開盤價
            
            # 獲取對應的分析數據（使用完整數據進行信號分析）
            data_4h_filtered = analysis_data_4h[analysis_data_4h.index <= current_time]
            data_1h_filtered = analysis_data_1h[analysis_data_1h.index <= current_time]
            
            if len(data_4h_filtered) < 50 or len(data_1h_filtered) < 50:
                continue
            
            # 處理待進場信號（在新K線開盤時進場）
            if pending_signal is not None and position is None:
                entry_price = current_open  # 使用開盤價進場
                
                # 顯示進場時的OHLC數據供驗證
                print(f"  📋 進場K線OHLC數據 ({self.format_taiwan_time(current_time)}):")
                print(f"   開盤價: ${current_open:.2f}")
                print(f"   最高價: ${current_high:.2f}")
                print(f"   最低價: ${current_low:.2f}")
                print(f"   收盤價: ${current_price:.2f}")
                print(f"   成交量: {row['volume']:.0f}")
                print(f"   進場價: ${entry_price:.2f} (使用開盤價)")
                
                if pending_signal['type'] == 'long':
                    position = 'long'
                    # 複利模式：保證金基於當前總資金計算，實現複利效果
                    position_value = capital * config.POSITION_SIZE
                    # 槓桿合約：實際控制的名義價值
                    notional_value = position_value * config.LEVERAGE
                    position_size = notional_value / entry_price
                    
                    # 計算停損停利
                    atr = pending_signal['atr']
                    stop_loss = entry_price - (atr * config.STOP_LOSS_MULTIPLIER)
                    take_profit = entry_price + (atr * config.STOP_LOSS_MULTIPLIER * config.RISK_REWARD_RATIO)
                    
                    # 槓桿交易只占用保證金，不需要全額資金
                    margin_used = position_value  # 保證金 = 名義價值 / 槓桿
                    capital -= margin_used  # 扣除保證金
                    entry_time = current_time
                    
                    print(f"📥 {self.format_taiwan_time(current_time)} 做多進場 - 價格: ${entry_price:.2f}, 停損: ${stop_loss:.2f}, 停利: ${take_profit:.2f}")
                    print(f"💰 倉位大小: {position_size:.4f} {base_currency} (名義價值 ${notional_value:.2f}, {config.LEVERAGE}x 槓桿)")
                    print(f"💳 保證金占用: ${margin_used:.2f}")
                    
                    # 記錄進場日誌
                    entry_msg = f"{self.format_taiwan_time(current_time)} 做多進場 - 價格: ${entry_price:.2f}, 停損: ${stop_loss:.2f}, 停利: ${take_profit:.2f}, 倉位: {position_size:.4f} {base_currency}, 槓桿: {config.LEVERAGE}x"
                    self.logger.info(entry_msg)
                
                elif pending_signal['type'] == 'short':
                    position = 'short'
                    # 複利模式：保證金基於當前總資金計算，實現複利效果
                    position_value = capital * config.POSITION_SIZE
                    # 槓桿合約：實際控制的名義價值
                    notional_value = position_value * config.LEVERAGE
                    position_size = notional_value / entry_price
                    
                    # 計算停損停利
                    atr = pending_signal['atr']
                    stop_loss = entry_price + (atr * config.STOP_LOSS_MULTIPLIER)
                    take_profit = entry_price - (atr * config.STOP_LOSS_MULTIPLIER * config.RISK_REWARD_RATIO)
                    
                    # 槓桿交易只占用保證金
                    margin_used = position_value  # 保證金 = 名義價值 / 槓桿
                    capital -= margin_used  # 扣除保證金（做空也需要保證金）
                    entry_time = current_time
                    
                    print(f"📥 {self.format_taiwan_time(current_time)} 做空進場 - 價格: ${entry_price:.2f}, 停損: ${stop_loss:.2f}, 停利: ${take_profit:.2f}")
                    print(f"💰 倉位大小: {position_size:.4f} {base_currency} (名義價值 ${notional_value:.2f}, {config.LEVERAGE}x 槓桿)")
                    print(f"💳 保證金占用: ${margin_used:.2f}")
                    
                    # 記錄進場日誌
                    entry_msg = f"{self.format_taiwan_time(current_time)} 做空進場 - 價格: ${entry_price:.2f}, 停損: ${stop_loss:.2f}, 停利: ${take_profit:.2f}, 倉位: {position_size:.4f} {base_currency}, 槓桿: {config.LEVERAGE}x"
                    self.logger.info(entry_msg)
                
                # 清除待進場信號
                pending_signal = None
            
            # 檢查停損停利（使用更精確的邏輯）
            if position is not None:
                exit_price = None
                exit_reason = None
                
                # 修正爆倉價格計算
                initial_margin_ratio = 1 / config.LEVERAGE  # 初始保證金率 = 1/槓桿
                maintenance_margin_ratio = config.MAINTENANCE_MARGIN_RATIO  # 維持保證金率
                
                if position == 'long':
                    # 做多爆倉價格：當虧損達到保證金的95%時爆倉
                    max_loss_ratio = 0.95  # 最大虧損比例
                    liquidation_price = entry_price * (1 - max_loss_ratio / config.LEVERAGE)
                else:  # short
                    # 做空爆倉價格：當虧損達到保證金的95%時爆倉
                    max_loss_ratio = 0.95  # 最大虧損比例
                    liquidation_price = entry_price * (1 + max_loss_ratio / config.LEVERAGE)
                
                # 優先檢查是否觸及爆倉（使用最高最低價）
                if config.MARGIN_MODE == "isolated":
                    if position == 'long' and current_low <= liquidation_price:
                        # 做多爆倉：最低價觸及爆倉價格，虧損全部保證金
                        exit_price = liquidation_price
                        exit_reason = '爆倉'
                        print(f"⚠️  做多爆倉！最低價 ${current_low:.2f} 觸及爆倉價格 ${liquidation_price:.2f}")
                    elif position == 'short' and current_high >= liquidation_price:
                        # 做空爆倉：最高價觸及爆倉價格，虧損全部保證金
                        exit_price = liquidation_price
                        exit_reason = '爆倉'
                        print(f"⚠️  做空爆倉！最高價 ${current_high:.2f} 觸及爆倉價格 ${liquidation_price:.2f}")
                
                # 如果沒有爆倉，檢查停損停利（使用最高最低價）
                if exit_price is None:
                    if position == 'long':
                        # 做多檢查：用最低價檢查停損，最高價檢查停利
                        if current_low <= stop_loss:
                            exit_price = stop_loss
                            exit_reason = '停損'
                        elif current_high >= take_profit:
                            exit_price = take_profit
                            exit_reason = '停利'
                    elif position == 'short':
                        # 做空檢查：用最高價檢查停損，最低價檢查停利
                        if current_high >= stop_loss:
                            exit_price = stop_loss
                            exit_reason = '停損'
                        elif current_low <= take_profit:
                            exit_price = take_profit
                            exit_reason = '停利'
                
                # 執行出場
                if exit_price is not None:
                    # 修正爆倉損益計算
                    if exit_reason == '爆倉':
                        # 爆倉時虧損全部保證金
                        pnl = -margin_used
                        capital += 0  # 爆倉時保證金全部虧損，不返還
                    else:
                        # 正常出場的槓桿合約損益計算
                        if position == 'long':
                            # 做多出場：價差 × 倉位大小
                            pnl = (exit_price - entry_price) * position_size
                        else:  # short
                            # 做空出場：反向價差 × 倉位大小
                            pnl = (entry_price - exit_price) * position_size
                        
                        # 返還保證金並加上損益
                        capital += margin_used + pnl
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'side': position,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'reason': exit_reason,
                        'leverage': config.LEVERAGE,
                        'margin_used': margin_used
                    })
                    
                    # 計算ROI（相對於保證金）
                    roi = (pnl / margin_used) * 100
                    
                    print(f"📤 {self.format_taiwan_time(current_time)} {position} 出場 - 價格: ${exit_price:.2f}, 損益: ${pnl:+.2f}, ROI: {roi:+.1f}%, 原因: {exit_reason}")
                    print()  # 出場後空行
                    
                    # 記錄出場日誌
                    exit_msg = f"{self.format_taiwan_time(current_time)} {position} 出場 - 價格: ${exit_price:.2f}, 損益: ${pnl:+.2f}, ROI: {roi:+.1f}%, 原因: {exit_reason}"
                    self.logger.info(exit_msg)
                    self.logger.info("")  # 出場後空行
                    
                    position = None
            
            # 檢查進場信號（如果沒有持倉且沒有待進場信號）
            if position is None and pending_signal is None:
                # 分析做多信號
                long_signal = self.signal_analyzer.analyze_long_signal(data_4h_filtered, data_1h_filtered)
                # 分析做空信號
                short_signal = self.signal_analyzer.analyze_short_signal(data_4h_filtered, data_1h_filtered)
                
                if long_signal['signal']:
                    # 記錄待進場信號，下一根K線開盤時進場
                    pending_signal = {
                        'type': 'long',
                        'atr': long_signal['atr'],
                        'time': current_time
                    }
                    
                    print(f"🔔 {self.format_taiwan_time(current_time)} 做多信號確認 - 下一根K線進場")
                    print(f"📊 MACD 1hr: {data_1h_filtered['macd_histogram'].iloc[-1]:.6f}, MACD 4hr: {data_4h_filtered['macd_histogram'].iloc[-1]:.6f}")
                
                elif short_signal['signal']:
                    # 記錄待進場信號，下一根K線開盤時進場
                    pending_signal = {
                        'type': 'short',
                        'atr': short_signal['atr'],
                        'time': current_time
                    }
                    
                    print(f"🔔 {self.format_taiwan_time(current_time)} 做空信號確認 - 下一根K線進場")
                    print(f"📊 MACD 1hr: {data_1h_filtered['macd_histogram'].iloc[-1]:.6f}, MACD 4hr: {data_4h_filtered['macd_histogram'].iloc[-1]:.6f}")
        
        # 如果最後還有持倉，強制平倉
        if position is not None:
            final_price = data_1h['close'].iloc[-1]
            final_time = data_1h.index[-1]
            
            # 槓桿合約強制平倉損益計算
            if position == 'long':
                # 做多強制平倉
                pnl = (final_price - entry_price) * position_size
            else:  # short
                # 做空強制平倉
                pnl = (entry_price - final_price) * position_size
            
            # 返還保證金並加上損益
            capital += margin_used + pnl
            
            trades.append({
                'entry_time': entry_time,
                'exit_time': final_time,
                'side': position,
                'entry_price': entry_price,
                'exit_price': final_price,
                'pnl': pnl,
                'reason': '強制平倉',
                'leverage': config.LEVERAGE,
                'margin_used': margin_used
            })
            
            roi = (pnl / margin_used) * 100
            print(f"📤 {self.format_taiwan_time(final_time)} {position} 強制平倉 - 價格: ${final_price:.2f}, 損益: ${pnl:+.2f}, ROI: {roi:+.1f}%")
            print()
            
            # 記錄強制平倉日誌
            force_close_msg = f"{self.format_taiwan_time(final_time)} {position} 強制平倉 - 價格: ${final_price:.2f}, 損益: ${pnl:+.2f}, ROI: {roi:+.1f}%"
            self.logger.info(force_close_msg)
            self.logger.info("")  # 強制平倉後空行
        
        # 如果最後還有待進場信號，取消它
        if pending_signal is not None:
            print(f"⚠️  回測結束，取消待進場的{pending_signal['type']}信號")
        
        # 計算績效統計
        if trades:
            df_trades = pd.DataFrame(trades)
            
            total_pnl = df_trades['pnl'].sum()
            win_trades = df_trades[df_trades['pnl'] > 0]
            lose_trades = df_trades[df_trades['pnl'] <= 0]
            
            win_rate = len(win_trades) / len(df_trades) * 100
            avg_win = win_trades['pnl'].mean() if len(win_trades) > 0 else 0
            avg_loss = lose_trades['pnl'].mean() if len(lose_trades) > 0 else 0
            best_trade = df_trades['pnl'].max()
            worst_trade = df_trades['pnl'].min()
        else:
            total_pnl = 0
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            best_trade = 0
            worst_trade = 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'total_pnl': total_pnl,
            'total_return': (capital - self.initial_capital) / self.initial_capital * 100,
            'trades': trades,
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade
        }
    
    def calculate_buy_hold_return(self, data: pd.DataFrame) -> float:
        """計算買入持有策略的報酬率"""
        if data is None or data.empty:
            return 0
        
        initial_price = data['close'].iloc[0]
        final_price = data['close'].iloc[-1]
        return (final_price - initial_price) / initial_price * 100


def run_backtest(symbol: str = None, days: Optional[int] = None, 
                warmup_days: Optional[int] = None,
                initial_capital: float = 10000.0) -> Dict:
    """
    執行完整的回測流程
    
    Args:
        symbol: 交易對符號（None 表示使用 config 預設值）
        days: 回測天數（None 表示使用 config 預設值）
        warmup_days: 預熱天數（用於技術指標計算，None 表示使用 config 預設值）
        initial_capital: 初始資金
        
    Returns:
        回測結果字典
    """
    # 設定日誌
    logger = setup_backtest_logging()
    
    # 使用預設參數
    if symbol is None:
        symbol = config.SYMBOL
    if days is None:
        days = config.BACKTEST_DAYS
    if warmup_days is None:
        warmup_days = config.WARMUP_DAYS
        
    print(f"🚀 {symbol} MACD 策略真實數據回測 (Binance 數據)")
    print("=" * 60)
    
    # 記錄回測開始
    logger.info(f"回測開始 - 交易對: {symbol}, 回測天數: {days}, 預熱天數: {warmup_days}, 初始資金: ${initial_capital}")
    
    # 計算日期範圍
    data_end_date = datetime.now()
    actual_end_date = data_end_date
    actual_start_date = actual_end_date - timedelta(days=days)
    data_start_date = actual_start_date - timedelta(days=warmup_days)
    
    # 格式化日期字串
    data_end = data_end_date.strftime('%Y-%m-%d')
    actual_end = actual_end_date.strftime('%Y-%m-%d')
    actual_start = actual_start_date.strftime('%Y-%m-%d')
    data_start = data_start_date.strftime('%Y-%m-%d')
    
    print(f"📅 數據獲取期間: {data_start} 到 {data_end} (包含 {warmup_days} 天預熱期)")
    print(f"📅 實際回測期間: {actual_start} 到 {actual_end} ({days} 天)")
    print()
    
    # 獲取數據
    print(f"📡 正在從 Binance API 獲取 {symbol} 1h 數據...")
    data_1h_raw = get_binance_klines(symbol, '1h', data_start, data_end)
    
    if data_1h_raw is None:
        print("❌ 無法獲取1小時數據，回測終止")
        return None
    
    print(f"✅ 成功獲取 {len(data_1h_raw)} 筆 {symbol} 1h 數據（含預熱期）")
    
    print(f"📡 正在從 Binance API 獲取 {symbol} 4h 數據...")
    data_4h_raw = get_binance_klines(symbol, '4h', data_start, data_end)
    
    if data_4h_raw is None:
        print("❌ 無法獲取4小時數據，回測終止")
        return None
    
    print(f"✅ 成功獲取 {len(data_4h_raw)} 筆 {symbol} 4h 數據（含預熱期）")
    
    # 計算技術指標
    print("📊 計算技術指標...")
    
    data_1h_full = TechnicalIndicators.calculate_macd(data_1h_raw)
    data_1h_full = TechnicalIndicators.calculate_atr(data_1h_full)
    
    data_4h_full = TechnicalIndicators.calculate_macd(data_4h_raw)
    
    # 排除最新的未完成4小時K線
    if len(data_4h_full) > 1:
        data_4h_full = data_4h_full.iloc[:-1].copy()
        print(f"⚠️  為確保數據一致性，排除最新的未完成4小時K線")
    
    print("✅ 技術指標計算完成")
    
    # 提取實際回測期間的數據
    actual_start_timestamp = pd.Timestamp(actual_start_date, tz='UTC')
    data_1h_with_indicators = data_1h_full[data_1h_full.index >= actual_start_timestamp].copy()
    data_4h_with_indicators = data_4h_full[data_4h_full.index >= actual_start_timestamp].copy()
    
    print(f"📊 實際回測數據：1h={len(data_1h_with_indicators)} 筆，4h={len(data_4h_with_indicators)} 筆")
    print(f"📊 預熱期修正：使用 {warmup_days} 天歷史數據確保指標準確性")
    print()
    
    # 顯示使用的參數
    print("📋 使用策略參數:")
    print(f"   回測天數: {days}")
    print(f"   預熱天數: {warmup_days}")
    print(f"   MACD: ({config.MACD_FAST}, {config.MACD_SLOW}, {config.MACD_SIGNAL})")
    print(f"   ATR 週期: {config.ATR_PERIOD}")
    print(f"   最少連續直方圖: {config.MIN_CONSECUTIVE_BARS}")
    print(f"   停損倍數: {config.STOP_LOSS_MULTIPLIER}")
    print(f"   風報比: {config.RISK_REWARD_RATIO}")
    print(f"   倉位大小: {config.POSITION_SIZE * 100}%")
    print(f"   槓桿倍數: {config.LEVERAGE}x (合約交易)")
    print(f"   保證金模式: {'逐倉' if config.MARGIN_MODE == 'isolated' else '全倉'}")
    print(f"   維持保證金比率: {config.MAINTENANCE_MARGIN_RATIO * 100}% (相對於初始保證金)")
    print()
    
    # 創建回測引擎並執行回測
    engine = BacktestEngine(initial_capital=initial_capital)
    results = engine.execute_backtest(data_1h_with_indicators, data_4h_with_indicators, 
                                     data_1h_full, data_4h_full, symbol=symbol)
    
    # 計算買入持有基準
    buy_hold_return = engine.calculate_buy_hold_return(data_1h_with_indicators)
    
    # 顯示回測報告
    print()
    print("=" * 70)
    print(f"📊 {symbol} MACD 策略真實數據回測報告 (Binance 數據)")
    print("=" * 70)
    
    # 顯示基本信息
    start_date = data_1h_with_indicators.index[0].strftime('%Y-%m-%d')
    end_date = data_1h_with_indicators.index[-1].strftime('%Y-%m-%d')
    print(f"📅 回測期間: {start_date} 到 {end_date}")
    print(f"💰 初始資金: ${results['initial_capital']:,.2f}")
    print(f"💰 最終資金: ${results['final_capital']:,.2f}")
    print(f"📈 總報酬率: {results['total_return']:+.2f}%")
    print(f"💵 總損益: ${results['total_pnl']:+,.2f}")
    print()
    
    # 顯示交易統計
    print("📊 交易統計:")
    print(f"   總交易次數: {results['total_trades']}")
    if results['total_trades'] > 0:
        # 使用回測引擎內部已計算的統計數據，確保一致性
        win_trades_count = len([t for t in results['trades'] if t['pnl'] > 0])
        lose_trades_count = len([t for t in results['trades'] if t['pnl'] <= 0])
        
        # 數據一致性檢查
        total_check = win_trades_count + lose_trades_count
        if total_check != results['total_trades']:
            logger.warning(f"統計數據不一致: 勝{win_trades_count} + 負{lose_trades_count} = {total_check} ≠ 總數{results['total_trades']}")
            print(f"   ⚠️ 統計數據異常: 勝{win_trades_count} + 負{lose_trades_count} = {total_check} ≠ 總數{results['total_trades']}")
        
        # 檢查是否有損益為0的交易（平手）
        draw_trades_count = len([t for t in results['trades'] if t['pnl'] == 0])
        if draw_trades_count > 0:
            print(f"   獲利交易: {win_trades_count}")
            print(f"   虧損交易: {lose_trades_count - draw_trades_count}")
            print(f"   平手交易: {draw_trades_count}")
        else:
            print(f"   獲利交易: {win_trades_count}")
            print(f"   虧損交易: {lose_trades_count}")
        
        print(f"   勝率: {results['win_rate']:.1f}%")
        print(f"   平均每筆損益: ${results['total_pnl']/results['total_trades']:+.2f}")
        print(f"   平均獲利: ${results['avg_win']:+.2f}")
        print(f"   平均虧損: ${results['avg_loss']:+.2f}")
        print(f"   最佳交易: ${results['best_trade']:+.2f}")
        print(f"   最差交易: ${results['worst_trade']:+.2f}")
        
        # 額外的統計分析
        if win_trades_count > 0 and lose_trades_count > 0:
            profit_factor = abs(results['avg_win'] * win_trades_count / (results['avg_loss'] * lose_trades_count))
            print(f"   獲利因子: {profit_factor:.2f}")
    else:
        print("   無交易記錄")
    print()
    
    # 顯示基準比較
    print("🔄 基準比較:")
    print(f"   買入持有報酬: {buy_hold_return:+.2f}%")
    print(f"   策略超額報酬: {results['total_return'] - buy_hold_return:+.2f}%")
    print()
    
    # 記錄回測結果到日誌
    logger.info(f"回測完成 - 總報酬率: {results['total_return']:+.2f}%, 總交易: {results['total_trades']}, 勝率: {results['win_rate']:.1f}%")
    logger.info(f"基準比較 - 買入持有: {buy_hold_return:+.2f}%, 策略超額: {results['total_return'] - buy_hold_return:+.2f}%")
    
    # 數據來源信息
    print("📊 數據來源:")
    print(f"   來源: Binance API")
    print(f"   交易對: {symbol}")
    print(f"   回測天數: {days} 天")
    print(f"   時間框架: 1小時 + 4小時")
    print(f"   數據筆數: 1h={len(data_1h_with_indicators)}, 4h={len(data_4h_with_indicators)}")
    print(f"   價格範圍: ${data_1h_with_indicators['close'].min():.2f} - ${data_1h_with_indicators['close'].max():.2f}")
    print(f"   預熱天數: {warmup_days} 天")
    
    return results 

def main():
    """直接執行回測的主函數"""
    print("🚀 啟動 MACD 策略回測")
    print("=" * 50)
    
    try:
        results = run_backtest(symbol=None)
        
        if results:
            print("\n✅ 回測完成！")
        else:
            print("\n❌ 回測失敗！")
            
    except KeyboardInterrupt:
        print("\n⏹️ 使用者中斷執行")
    except Exception as e:
        print(f"\n❌ 執行錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 