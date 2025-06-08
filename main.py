#!/usr/bin/env python3
"""
MACD交易策略主程式入口
提供回測和實時監控功能
"""

import sys
import os
import argparse
from datetime import datetime

# 添加 src 路徑到系統路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from macd_strategy.backtest.backtest_engine import run_backtest
from macd_strategy.strategy.trading_strategy import MacdTradingStrategy
from macd_strategy.core import config


def run_backtest_mode(days: int = None, initial_capital: float = 10000.0):
    """運行回測模式"""
    if days is None:
        days = config.BACKTEST_DAYS
    
    print("🚀 啟動MACD策略回測模式")
    print("=" * 50)
    
    results = run_backtest(
        symbol=config.SYMBOL,
        days=days,
        initial_capital=initial_capital
    )
    
    return results


def run_monitor_mode(duration_hours: float = 24):
    """運行實時監控模式"""
    print("📡 啟動MACD策略實時監控模式")
    print("=" * 50)
    print("⚠️  注意：此模式僅監控信號，不會自動執行交易")
    print("💡 檢測到信號時請手動到交易所執行")
    print()
    
    strategy = MacdTradingStrategy()
    results = strategy.run_strategy(duration_hours=duration_hours)
    
    return results


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='MACD交易策略')
    parser.add_argument('--mode', choices=['backtest', 'monitor'], 
                       default='backtest', help='運行模式')
    parser.add_argument('--days', type=int, default=None,
                       help='回測天數 (僅適用於backtest模式)')
    parser.add_argument('--capital', type=float, default=10000.0,
                       help='初始資金 (僅適用於backtest模式)')
    parser.add_argument('--hours', type=float, default=24,
                       help='監控時長小時數 (僅適用於monitor模式)')
    
    args = parser.parse_args()
    
    print("🎯 MACD 交易策略系統")
    print(f"📅 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 交易對: {config.SYMBOL}")
    print(f"📋 交易所: {config.EXCHANGE}")
    print()
    
    try:
        if args.mode == 'backtest':
            results = run_backtest_mode(args.days, args.capital)
            print("\n✅ 回測完成")
            
        elif args.mode == 'monitor':
            results = run_monitor_mode(args.hours)
            print("\n✅ 監控完成")
            
    except KeyboardInterrupt:
        print("\n⏹️ 使用者中斷執行")
    except Exception as e:
        print(f"\n❌ 執行錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 