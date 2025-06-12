"""
MACD 交易策略配置模板
複製此文件為 config.py 並修改參數
簡化版本 - 專注於核心配置
"""

# 交易對和交易所配置
SYMBOL = "BTCUSDT"
EXCHANGE = "binance"

# 數據配置
WARMUP_DAYS = 45

# MACD 指標參數
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ATR 指標參數
ATR_PERIOD = 21

# 信號確認參數
MIN_CONSECUTIVE_BARS = 4

# 回測配置
BACKTEST_DAYS = 365
INITIAL_CAPITAL = 10000  # 初始資金，可在命令行修改

# 風險管理參數
STOP_LOSS_MULTIPLIER = 1.5
RISK_REWARD_RATIO = 1.2
RISK_PER_TRADE = 0.02  # 每筆交易風險2%
POSITION_SIZE = 0.05
LEVERAGE = 50
MARGIN_MODE = "isolated"
MAINTENANCE_MARGIN_RATIO = 0.05

# 日誌配置
LOG_LEVEL = "INFO"
LOG_FILE = "trading_log.txt"  # 相對於logs目錄
BACKTEST_LOG_FILE = "backtest_log.txt"  # 相對於logs目錄
SIGNAL_LOG_FILE = "signal_log.txt"  # 相對於logs目錄

# 圖表配置
CHART_CONFIG = {
    "SAVE_DIR": "logs",
    "DPI": 300,
    "FIGURE_SIZE": (15, 10),
    "CHART_STYLE": "default"
} 