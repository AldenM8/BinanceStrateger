"""
MACD 交易策略配置模板
複製此文件為 config.py 並修改參數
"""

# === 交易對設定 ===
SYMBOL = "BTCUSDT"         # 交易對 (建議: BTCUSDT, ETHUSDT, ADAUSDT 等)
EXCHANGE = "binance"       # 交易所

# === 時間框架設定 ===
TIMEFRAME_1H = "1h"        # 1小時時間框架
TIMEFRAME_4H = "4h"        # 4小時時間框架

# === 數據預熱設定 ===
WARMUP_DAYS = 45           # 預熱天數 (建議30-60天，確保技術指標準確)

# === MACD 指標參數 ===
MACD_FAST = 12             # 快線 EMA 週期 (建議8-15)
MACD_SLOW = 26             # 慢線 EMA 週期 (建議20-30)
MACD_SIGNAL = 9            # 信號線 EMA 週期 (建議7-12)

# === ATR 指標參數 ===
ATR_PERIOD = 21            # ATR 計算週期 (建議14-28)

# === 交易信號參數 ===
MIN_CONSECUTIVE_BARS = 4   # 最少連續直方圖數量 (建議3-6)

# === 回測參數 ===
BACKTEST_DAYS = 365        # 回測天數 (建議180-720天)

# === 風險管理參數 ===
STOP_LOSS_MULTIPLIER = 1.5    # 停損倍數 (ATR的倍數，建議1.0-3.0)
RISK_REWARD_RATIO = 1.2       # 風險報酬比 (建議1.0-2.0)
POSITION_SIZE = 0.05           # 倉位大小比例 (5%，建議0.02-0.2)
LEVERAGE = 50                  # 槓桿倍數 (建議10-100x)
MARGIN_MODE = "isolated"       # 保證金模式: "isolated" (逐倉) 或 "cross" (全倉)

# === 維持保證金比率 ===
# 幣安永續合約維持保證金比率參考:
# BTCUSDT: 0.40% (0-50,000 USDT), 0.50% (50,000-250,000 USDT)
# ETHUSDT: 0.40% (0-50,000 USDT), 0.50% (50,000-250,000 USDT)
# 詳細請查詢交易所官方文檔
MAINTENANCE_MARGIN_RATIO = 0.05  # 5% (保守設定，實際可能更低)

# === 日誌設定 ===
LOG_LEVEL = "INFO"         # 日誌級別: DEBUG, INFO, WARNING, ERROR

# === 高頻模式設定 ===
HIGH_FREQ_MODE = {
    "ENTRY_CHECK_SECOND": 5,  # 每小時第N秒檢查進場信號
}

# === 實盤交易設定 (可選) ===
# LIVE_TRADING = False  # 是否啟用實盤交易
# MAX_POSITION_SIZE = 1000  # 最大倉位金額 (USDT) 