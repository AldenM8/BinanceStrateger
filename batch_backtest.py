#!/usr/bin/env python3
"""
批量回測腳本 - 使用不同天數配置運行MACD策略回測
生成包含天數、總報酬率、勝率、資產價值的CSV文件
"""

import sys
import os
import pandas as pd
from datetime import datetime
import tempfile
import shutil

# 添加 src 路徑到系統路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from macd_strategy.backtest import run_backtest
from macd_strategy.core import config


def run_batch_backtest(backtest_days_list, initial_capital=10000.0):
    """
    批量運行不同天數的回測
    
    Args:
        backtest_days_list: 回測天數列表
        initial_capital: 初始資金
        
    Returns:
        包含所有回測結果的 DataFrame
    """
    results = []
    
    # 備份原始配置
    original_backtest_days = config.BACKTEST_DAYS
    
    print("🚀 開始批量回測...")
    print(f"📊 回測天數: {backtest_days_list}")
    print(f"💰 初始資金: ${initial_capital:,.2f}")
    print("=" * 60)
    
    for i, days in enumerate(backtest_days_list, 1):
        print(f"\n📈 [{i}/{len(backtest_days_list)}] 執行 {days} 天回測...")
        print("-" * 40)
        
        try:
            # 臨時修改配置
            config.BACKTEST_DAYS = days
            
            # 運行回測
            result = run_backtest(
                symbol=config.SYMBOL,
                days=days,
                initial_capital=initial_capital
            )
            
            if result:
                # 提取所需的統計數據
                record = {
                    '天數': days,
                    '總報酬率': round(result['total_return'], 2),
                    '勝率': round(result['win_rate'], 2),
                    '資產價值': round(result['final_capital'], 2),
                    '總交易次數': result['total_trades'],
                    '總損益': round(result['total_pnl'], 2),
                    '初始資金': round(result['initial_capital'], 2)
                }
                
                results.append(record)
                
                print(f"✅ {days} 天回測完成")
                print(f"   總報酬率: {result['total_return']:+.2f}%")
                print(f"   勝率: {result['win_rate']:.2f}%")
                print(f"   資產價值: ${result['final_capital']:,.2f}")
                print(f"   總交易次數: {result['total_trades']}")
                
            else:
                print(f"❌ {days} 天回測失敗")
                
        except Exception as e:
            print(f"❌ {days} 天回測錯誤: {e}")
            continue
    
    # 恢復原始配置
    config.BACKTEST_DAYS = original_backtest_days
    
    print("\n" + "=" * 60)
    print("📊 批量回測完成")
    
    return pd.DataFrame(results)


def save_results_to_csv(df, filename=None):
    """
    將回測結果保存到CSV文件
    
    Args:
        df: 回測結果 DataFrame
        filename: 輸出文件名，None 則自動生成
        
    Returns:
        保存的文件路徑
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_results_{timestamp}.csv"
    
    # 確保 reports 目錄存在
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    filepath = os.path.join(reports_dir, filename)
    
    # 保存CSV文件，使用UTF-8編碼以支持中文
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    return filepath


def main():
    """主函數"""
    # 定義要測試的天數：7天 + 每月間隔直到720天
    backtest_days_list = [7] + list(range(30, 721, 30))  # 7, 30, 60, 90, ..., 720
    
    # 初始資金
    initial_capital = 10000.0
    
    print("🎯 MACD策略批量回測")
    print("=" * 50)
    print(f"📋 交易對: {config.SYMBOL}")
    print(f"📋 交易所: {config.EXCHANGE}")
    print(f"📋 策略參數:")
    print(f"   MACD: ({config.MACD_FAST}, {config.MACD_SLOW}, {config.MACD_SIGNAL})")
    print(f"   ATR週期: {config.ATR_PERIOD}")
    print(f"   停損倍數: {config.STOP_LOSS_MULTIPLIER}")
    print(f"   風報比: {config.RISK_REWARD_RATIO}")
    print(f"   倉位大小: {config.POSITION_SIZE * 100}%")
    print(f"   槓桿: {config.LEVERAGE}x")
    
    try:
        # 執行批量回測
        results_df = run_batch_backtest(backtest_days_list, initial_capital)
        
        if not results_df.empty:
            # 顯示結果摘要
            print("\n📊 回測結果摘要:")
            print("=" * 80)
            print(results_df.to_string(index=False))
            
            # 保存到CSV
            csv_path = save_results_to_csv(results_df)
            print(f"\n💾 結果已保存到: {csv_path}")
            
            # 顯示最佳表現
            if len(results_df) > 0:
                best_return = results_df.loc[results_df['總報酬率'].idxmax()]
                best_winrate = results_df.loc[results_df['勝率'].idxmax()]
                
                print(f"\n🏆 最佳報酬率: {best_return['天數']}天 ({best_return['總報酬率']:+.2f}%)")
                print(f"🏆 最高勝率: {best_winrate['天數']}天 ({best_winrate['勝率']:.2f}%)")
            
        else:
            print("❌ 沒有成功的回測結果")
            
    except KeyboardInterrupt:
        print("\n⏹️ 使用者中斷執行")
    except Exception as e:
        print(f"\n❌ 執行錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 