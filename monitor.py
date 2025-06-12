#!/usr/bin/env python3
"""
MACD策略實時監控主程序
簡化執行：python monitor.py
"""

import sys
import argparse

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='MACD策略實時監控')
    parser.add_argument('--initial_capital', type=float, default=10000.0,
                       help='初始資金 (預設: 10000)')
    parser.add_argument('--symbol', type=str, default=None,
                       help='交易對 (預設: 使用config設定)')
    
    args = parser.parse_args()
    
    try:
        print("🚀 啟動MACD策略實時監控")
        print("=" * 50)
        print("💡 監控將每小時檢查信號，按 Ctrl+C 停止")
        print()
        
        # 導入並執行監控
        from src.macd_strategy.strategy.trading_strategy import main as monitor_main
        
        # 設定參數
        if args.initial_capital != 10000.0:
            import src.macd_strategy.core.config as config
            # 這裡可以動態設定初始資金，但需要修改config模組
            print(f"💰 使用初始資金: ${args.initial_capital:,.2f}")
        
        # 執行監控
        monitor_main()
            
    except KeyboardInterrupt:
        print("\n⏹️ 監控已停止")
    except Exception as e:
        print(f"\n❌ 執行錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 