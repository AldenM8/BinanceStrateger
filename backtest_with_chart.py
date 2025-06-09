#!/usr/bin/env python3
"""
MACD 策略回測（帶資產變化圖表）
執行回測並生成總資產變化的折線圖
"""

import sys
import os
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.macd_strategy.backtest.backtest_engine import run_backtest
from src.macd_strategy.core import config

def main():
    """主程式"""
    print("🚀 MACD 策略回測（帶圖表生成）")
    print("=" * 60)
    
    # 顯示配置信息
    print(f"📊 交易對: {config.SYMBOL}")
    print(f"📅 回測天數: {config.BACKTEST_DAYS}")
    print(f"🔧 MACD參數: 快線={config.MACD_FAST}, 慢線={config.MACD_SLOW}, 信號線={config.MACD_SIGNAL}")
    print(f"📈 最少連續直方圖: {config.MIN_CONSECUTIVE_BARS}")
    print(f"💰 初始資金: $10,000")
    print()
    
    try:
        # 確保logs目錄存在
        import os
        os.makedirs("logs", exist_ok=True)
        
        # 執行回測
        results = run_backtest(
            symbol=config.SYMBOL,
            days=config.BACKTEST_DAYS,
            initial_capital=10000.0
        )
        
        if results:
            print("\n✅ 回測完成！圖表已生成。")
            print(f"📊 總報酬率: {results['total_return']:+.2f}%")
            print(f"🎯 勝率: {results['win_rate']:.1f}%")
            print(f"📈 交易次數: {results['total_trades']}")
        else:
            print("❌ 回測失敗")
            
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 