"""
MACD 交易策略配置模板
複製此文件為 config.py 並修改參數
"""

# === 交易對設定 ===
SYMBOL = "ETHUSDT"         # 交易對
EXCHANGE = "binance"       # 交易所

# === 時間框架 ===
TIMEFRAME_1H = "1h"        # 1小時
TIMEFRAME_4H = "4h"        # 4小時

# === 指標預熱天數 ===
WARMUP_DAYS = 30           # 預熱天數

# === MACD 參數 ===
MACD_FAST = 6       # 快線 EMA 週期
MACD_SLOW = 13      # 慢線 EMA 週期
MACD_SIGNAL = 9     # 信號線 EMA 週期

# === ATR 參數 ===
ATR_PERIOD = 14     # ATR 計算週期

# === 交易信號參數 ===
MIN_CONSECUTIVE_BARS = 3   # 最少連續直方圖數量

# === 回測參數 ===
BACKTEST_DAYS = 720         # 回測天數

# === 風險管理參數 ===
STOP_LOSS_MULTIPLIER = 2.0    # 停損倍數 (ATR的倍數)
RISK_REWARD_RATIO = 1.1      # 風險報酬比
POSITION_SIZE = 0.1      # 倉位大小 (10%)
LEVERAGE = 80              # 槓桿倍數 (80x)
MARGIN_MODE = "isolated"   # 保證金模式: "isolated" (逐倉) 或 "cross" (全倉)

# === 維持保證金比率 ===
# 幣安 ETHUSDT 永續合約實際維持保證金比率: 0.40%
# 注意：不同持倉規模的維持保證金比率可能不同
# 0-50,000 USDT: 0.40%
# 50,000-250,000 USDT: 0.50% 
# 詳細請查詢交易所官方文檔
MAINTENANCE_MARGIN_RATIO = 0.004  # 0.40% (適用於小額持倉)

# === 日誌設定 ===
LOG_LEVEL = "INFO"
LOG_FILE = "logs/trading_log.txt"
BACKTEST_LOG_FILE = "logs/backtest_log.txt"

# === 高頻模式設定 ===
HIGH_FREQ_MODE = {
    "ENTRY_CHECK_SECOND": 5,  # 每小時第N秒檢查進場信號
}

# === 實盤交易設定 (可選) ===
# LIVE_TRADING = False  # 是否啟用實盤交易
# MAX_POSITION_SIZE = 1000  # 最大倉位金額 (USDT) 