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
LEVERAGE = 30                 # 槓桿倍數 (合約交易)
MARGIN_MODE = "isolated"      # 保證金模式: "isolated" (逐倉) 或 "cross" (全倉)

# 動態計算維持保證金比率
def calculate_maintenance_margin_ratio(leverage):
    """
    根據槓桿倍數動態計算建議的維持保證金比率係數
    參考真實交易所的風險控制標準
    """
    if leverage <= 10:
        return 0.6      # 低槓桿，較寬鬆
    elif leverage <= 25:
        return 0.5      # 中等槓桿
    elif leverage <= 50:
        return 0.4      # 高槓桿
    elif leverage <= 75:
        return 0.35     # 極高槓桿
    else:
        return 0.3      # 超高槓桿，更嚴格

# 使用動態計算或手動設定
MAINTENANCE_MARGIN_RATIO = calculate_maintenance_margin_ratio(LEVERAGE)  # 動態計算
# MAINTENANCE_MARGIN_RATIO = 0.4  # 或手動設定

# === 交易信號參數 ===
MIN_CONSECUTIVE_BARS = 5      # 最少連續直方圖數量

# === 回測參數 ===
BACKTEST_DAYS = 180           # 回測天數
WARMUP_DAYS = 60            # 預熱天數 (技術指標計算需要)

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
}

# === 實盤交易設定 ===
# LIVE_TRADING = False  # 是否啟用實盤交易
# MAX_POSITION_SIZE = 1000  # 最大倉位金額 (USDT) 