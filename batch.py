#!/usr/bin/env python3
"""
MACD策略批量回測主程序
簡化執行：python batch.py
"""

import sys
import argparse

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='MACD策略批量回測')
    parser.add_argument('--initial_capital', type=float, default=10000.0,
                       help='初始資金 (預設: 10000)')
    
    args = parser.parse_args()
    
    try:
        print("🚀 啟動MACD策略批量回測")
        print("=" * 50)
        print(f"💰 使用初始資金: ${args.initial_capital:,.2f}")
        print("💡 將測試不同天數的回測效果，請稍候...")
        print()
        
        # 執行批量回測
        exec(open('batch_backtest.py').read())
            
    except FileNotFoundError:
        print("❌ 找不到 batch_backtest.py 文件")
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 