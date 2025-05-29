#!/usr/bin/env python3
"""
回測引擎啟動器
直接執行: python backtest_engine.py
"""

import sys
from pathlib import Path

# 添加 src 目錄到 Python 路徑
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    from macd_strategy.backtest.backtest_engine import main
    main() 