#!/usr/bin/env python3
"""
交易策略啟動器
直接執行: python trading_strategy.py
"""

import sys
from pathlib import Path

# 添加 src 目錄到 Python 路徑
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def show_menu():
    """顯示選擇菜單"""
    print("🚀 MACD 交易策略")
    print("=" * 30)
    print("1. ⚡ 實時策略 (24小時)")
    print("2. 🧪 短期測試 (10分鐘)")
    print("3. ❌ 退出")
    print("=" * 30)

if __name__ == "__main__":
    from macd_strategy.strategy.trading_strategy import main, test_short_run
    
    while True:
        show_menu()
        choice = input("請選擇 (1-3): ").strip()
        
        if choice == "1":
            print("\n⚡ 啟動實時交易策略...")
            print("⚠️  按 Ctrl+C 可停止")
            print("-" * 40)
            try:
                main()
            except KeyboardInterrupt:
                print("\n⏹️ 策略已停止")
                
        elif choice == "2":
            print("\n🧪 執行10分鐘測試...")
            print("-" * 40)
            try:
                test_short_run()
            except KeyboardInterrupt:
                print("\n⏹️ 測試已停止")
                
        elif choice == "3":
            print("👋 再見！")
            break
            
        else:
            print("❌ 請輸入 1、2 或 3")
        
        print()  # 空行 