#!/usr/bin/env python3
"""
MACD策略回測主程序
簡化執行：python backtest.py
"""

import sys
import argparse
from src.macd_strategy.backtest.backtest_engine import run_backtest

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='MACD策略回測')
    parser.add_argument('--initial_capital', type=float, default=10000.0,
                       help='初始資金 (預設: 10000)')
    parser.add_argument('--days', type=int, default=None,
                       help='回測天數 (預設: 使用config設定)')
    parser.add_argument('--symbol', type=str, default=None,
                       help='交易對 (預設: 使用config設定)')
    
    args = parser.parse_args()
    
    try:
        print("🚀 啟動MACD策略回測")
        print("=" * 50)
        
        # 執行回測
        results = run_backtest(
            symbol=args.symbol,
            days=args.days,
            initial_capital=args.initial_capital
        )
        
        if results:
            print("\n✅ 回測完成！")
            print(f"📊 圖表已保存至 logs/ 資料夾")
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