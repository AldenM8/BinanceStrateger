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
POSITION_SIZE = 0.05
LEVERAGE = 50  # 預設槓桿，實際會根據持倉價值動態調整
MARGIN_MODE = "isolated"
MAINTENANCE_MARGIN_RATIO = 0.05  # 預設維持保證金比率，實際會動態調整

# 日誌配置
LOG_LEVEL = "INFO"
LOG_FILE = "trading_log.txt"  # 相對於logs目錄
BACKTEST_LOG_FILE = "backtest_log.txt"  # 相對於logs目錄
SIGNAL_LOG_FILE = "signal_log.txt"  # 相對於logs目錄

# 圖表配置
CHART_SAVE_DIR = "logs"
CHART_DPI = 300
CHART_FIGURE_SIZE = (15, 10)

# 幣安ETHUSDT槓桿分級制度 (根據名義持倉價值) - 完整12級
BINANCE_LEVERAGE_BRACKETS = [
    {
        "notional_min": 0,
        "notional_max": 50000,
        "max_leverage": 125,
        "maintenance_margin_rate": 0.004,  # 0.40%
        "maintenance_amount": 0
    },
    {
        "notional_min": 50000,
        "notional_max": 600000,
        "max_leverage": 100,
        "maintenance_margin_rate": 0.005,  # 0.50%
        "maintenance_amount": 50
    },
    {
        "notional_min": 600000,
        "notional_max": 3000000,
        "max_leverage": 75,
        "maintenance_margin_rate": 0.0065,  # 0.65%
        "maintenance_amount": 950
    },
    {
        "notional_min": 3000000,
        "notional_max": 12000000,
        "max_leverage": 50,
        "maintenance_margin_rate": 0.01,  # 1.00%
        "maintenance_amount": 11450
    },
    {
        "notional_min": 12000000,
        "notional_max": 50000000,
        "max_leverage": 25,
        "maintenance_margin_rate": 0.02,  # 2.00%
        "maintenance_amount": 131450
    },
    {
        "notional_min": 50000000,
        "notional_max": 65000000,
        "max_leverage": 20,
        "maintenance_margin_rate": 0.025,  # 2.50%
        "maintenance_amount": 381450
    },
    {
        "notional_min": 65000000,
        "notional_max": 150000000,
        "max_leverage": 10,
        "maintenance_margin_rate": 0.05,  # 5.00%
        "maintenance_amount": 2006450
    },
    {
        "notional_min": 150000000,
        "notional_max": 320000000,
        "max_leverage": 5,
        "maintenance_margin_rate": 0.10,  # 10.00%
        "maintenance_amount": 9506450
    },
    {
        "notional_min": 320000000,
        "notional_max": 400000000,
        "max_leverage": 4,
        "maintenance_margin_rate": 0.125,  # 12.50%
        "maintenance_amount": 17506450
    },
    {
        "notional_min": 400000000,
        "notional_max": 530000000,
        "max_leverage": 3,
        "maintenance_margin_rate": 0.15,  # 15.00%
        "maintenance_amount": 27506450
    },
    {
        "notional_min": 530000000,
        "notional_max": 800000000,
        "max_leverage": 2,
        "maintenance_margin_rate": 0.25,  # 25.00%
        "maintenance_amount": 80506450
    },
    {
        "notional_min": 800000000,
        "notional_max": 1200000000,
        "max_leverage": 1,
        "maintenance_margin_rate": 0.50,  # 50.00%
        "maintenance_amount": 280506450
    }
] 