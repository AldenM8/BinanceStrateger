#!/usr/bin/env python3
"""
MACD策略主程序
提供選單讓用戶選擇功能
"""

import sys
import os

def show_menu():
    """顯示主選單"""
    print("🚀 MACD短線交易策略")
    print("=" * 50)
    print("請選擇功能：")
    print()
    print("1. 📊 執行回測分析")
    print("2. 👁️  啟動實時監控")
    print("3. 📈 批量回測分析")
    print("4. ❌ 退出程序")
    print()

def run_backtest():
    """執行回測"""
    print("\n" + "="*50)
    print("📊 執行回測分析")
    print("="*50)
    
    try:
        capital = input("請輸入初始資金 (預設 10000): ").strip()
        if not capital:
            capital = 10000
        else:
            capital = float(capital)
        
        days = input("請輸入回測天數 (預設 360): ").strip()
        if not days:
            days = None
        else:
            days = int(days)
        
        print(f"\n🚀 開始回測 - 初始資金: ${capital:,.2f}")
        if days:
            print(f"📅 回測天數: {days}")
        
        from src.macd_strategy.backtest.backtest_engine import run_backtest
        results = run_backtest(initial_capital=capital, days=days)
        
        if results:
            print("\n✅ 回測完成！圖表已保存至 logs/ 資料夾")
        else:
            print("\n❌ 回測失敗！")
            
    except ValueError:
        print("❌ 輸入格式錯誤，請輸入數字")
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")

def run_monitor():
    """啟動監控"""
    print("\n" + "="*50)
    print("👁️ 啟動實時監控")
    print("="*50)
    
    try:
        capital = input("請輸入初始資金 (預設 10000): ").strip()
        if not capital:
            capital = 10000
        else:
            capital = float(capital)
        
        print(f"\n🚀 開始監控 - 初始資金: ${capital:,.2f}")
        print("💡 監控將每小時檢查信號，按 Ctrl+C 停止")
        print()
        
        from src.macd_strategy.strategy.trading_strategy import main as monitor_main
        monitor_main()
        
    except ValueError:
        print("❌ 輸入格式錯誤，請輸入數字")
    except KeyboardInterrupt:
        print("\n⏹️ 監控已停止")
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")

def run_batch_backtest():
    """執行批量回測"""
    print("\n" + "="*50)
    print("📈 批量回測分析")
    print("="*50)
    
    try:
        capital = input("請輸入初始資金 (預設 10000): ").strip()
        if not capital:
            capital = 10000
        else:
            capital = float(capital)
        
        print(f"\n🚀 開始批量回測 - 初始資金: ${capital:,.2f}")
        print("💡 將測試不同天數的回測效果，請稍候...")
        print()
        
        # 執行批量回測
        exec(open('batch_backtest.py').read())
        
    except ValueError:
        print("❌ 輸入格式錯誤，請輸入數字")
    except FileNotFoundError:
        print("❌ 找不到 batch_backtest.py 文件")
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")

def main():
    """主函數"""
    while True:
        try:
            show_menu()
            choice = input("請輸入選項 (1-4): ").strip()
            
            if choice == '1':
                run_backtest()
            elif choice == '2':
                run_monitor()
            elif choice == '3':
                run_batch_backtest()
            elif choice == '4':
                print("\n👋 感謝使用！")
                break
            else:
                print("\n❌ 無效選項，請輸入 1-4")
            
            if choice in ['1', '2', '3']:
                input("\n按 Enter 鍵返回主選單...")
                print("\n" * 2)  # 清空一些行
                
        except KeyboardInterrupt:
            print("\n\n👋 程序已退出")
            break
        except Exception as e:
            print(f"\n❌ 程序錯誤: {e}")
            input("按 Enter 鍵返回主選單...")

if __name__ == "__main__":
    main() 