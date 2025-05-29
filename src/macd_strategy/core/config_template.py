"""
MACD 交易策略配置模板
複製此文件為 config.py 並修改參數
"""

# === MACD 參數 ===
MACD_FAST = 6       # 快線 EMA 週期
MACD_SLOW = 13      # 慢線 EMA 週期
MACD_SIGNAL = 9     # 信號線 EMA 週期

# === ATR 參數 ===
ATR_PERIOD = 14     # ATR 計算週期

# === 風險管理參數 ===
STOP_LOSS_MULTIPLIER = 2.0    # 停損倍數 (ATR的倍數)
RISK_REWARD_RATIO = 1      # 風險報酬比
POSITION_SIZE = 0.1           # 倉位大小 (10%)

# === 交易信號參數 ===
MIN_CONSECUTIVE_BARS = 5      # 最少連續直方圖數量

# === 回測參數 ===
BACKTEST_DAYS = 180           # 回測天數
WARMUP_DAYS = 100            # 預熱天數 (技術指標計算需要)
SKIP_BARS = 0               # 跳過前N筆數據 (避免指標初期誤差)

# === 交易對設定 ===
SYMBOL = "SOLUSDT"           # 交易對
EXCHANGE = "binance"         # 交易所

# === 時間框架 ===
TIMEFRAME_1H = "1h"          # 1小時
TIMEFRAME_4H = "4h"          # 4小時

# === 日誌設定 ===
LOG_LEVEL = "INFO"           # 日誌等級
LOG_FILE = "logs/trading_log.txt"  # 實時交易日誌文件
BACKTEST_LOG_FILE = "logs/backtest_log.txt"  # 回測日誌文件

# === 高頻模式設定 ===
HIGH_FREQ_MODE = {
    "ENTRY_CHECK_SECOND": 5,      # 每小時第N秒檢查進場信號
    "EXIT_CHECK_INTERVAL": 5,     # 每N秒檢查出場條件
    "USE_REALTIME_PRICE": True    # 是否使用即時價格
}

# === API 設定 (請在實際配置文件中填入) ===
# BINANCE_API_KEY = "your_api_key_here"
# BINANCE_SECRET_KEY = "your_secret_key_here"

# === 實盤交易設定 ===
# LIVE_TRADING = False  # 是否啟用實盤交易
# MAX_POSITION_SIZE = 1000  # 最大倉位金額 (USDT) 