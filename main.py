#!/usr/bin/env python3
"""
MACD 交易策略主程式
專案入口點
"""

import sys
import os
from pathlib import Path

# 添加 src 目錄到 Python 路徑
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from macd_strategy.backtest.backtest_engine import run_backtest
from macd_strategy.core.config import SYMBOL


def main():
    """主程式入口"""
    try:
        print("🚀 啟動 MACD 交易策略回測系統")
        print("=" * 60)
        
        # 執行回測（使用 config 中的預設參數）
        results = run_backtest(symbol=SYMBOL)
        
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