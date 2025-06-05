# MACD 交易策略

基於 MACD 指標的加密貨幣交易策略，支援回測和實時交易監控。

## 🚀 核心功能

### 📊 回測功能
- 使用 Binance 真實歷史數據
- 詳細的績效分析報告
- 可自定義策略參數

### ⚡ 實時監控
- 24/7 市場監控
- 自動信號檢測
- 風險管理機制

## 📈 策略說明

### 做多信號
- 1H MACD 直方圖第一根轉正
- 轉正前有連續4根以上負值
- 4H MACD 直方圖同樣為正值

### 做空信號  
- 1H MACD 直方圖第一根轉負
- 轉負前有連續4根以上正值
- 4H MACD 直方圖同樣為負值

### 風險控制
- 停損：ATR × 2.0
- 停利：停損 × 1.1（風報比1.1:1）

## ⚙️ 快速開始

### 1. 配置設定
```bash
# 複製配置模板
cp src/macd_strategy/core/config_template.py src/macd_strategy/core/config.py

# 編輯配置文件
# 根據需要修改交易參數、API 金鑰等設定
```

**重要：** `config.py` 文件已被 `.gitignore` 保護，不會被推送到版本控制，確保您的 API 金鑰和個人交易參數安全。

### 2. 執行回測
```bash
# 基本回測 (使用默認參數)
python main.py

# 自定義回測天數和初始資金
python main.py --mode backtest --days 30 --capital 10000

# 批量回測 (多種天數)
python batch_backtest.py
```

### 3. 實時監控
```bash
# 24小時監控 (僅監控信號，不自動交易)
python main.py --mode monitor

# 自定義監控時長
python main.py --mode monitor --hours 12
```

### 3. 自定義參數
編輯 `src/macd_strategy/core/config.py`：

```python
# MACD 參數
MACD_FAST = 6       # 快線週期
MACD_SLOW = 13      # 慢線週期
MACD_SIGNAL = 9     # 信號線週期

# 風險管理
STOP_LOSS_MULTIPLIER = 2.0    # 停損倍數
RISK_REWARD_RATIO = 1.1       # 風報比
POSITION_SIZE = 0.1           # 倉位大小(10%)
LEVERAGE = 80                 # 槓桿倍數

# 回測設定
BACKTEST_DAYS = 30           # 回測天數
```

## 📊 程式化使用

```python
from src.macd_strategy.backtest.backtest_engine import run_backtest

# 執行自定義回測
results = run_backtest(
    symbol='ETHUSDT',  # 可設定任何支援的交易對
    days=30,
    initial_capital=10000.0
)

print(f"總報酬率: {results['total_return']:.2f}%")
print(f"勝率: {results['win_rate']:.1f}%")
```

## 🎯 實時監控使用

```python
from src.macd_strategy.strategy.trading_strategy import MacdTradingStrategy

# 創建策略實例
strategy = MacdTradingStrategy()

# 運行24小時監控（僅監控信號，不自動交易）
results = strategy.run_strategy(duration_hours=24)
```

## 📁 專案結構

```
MACD_S/
├── src/macd_strategy/           # 策略核心
│   ├── core/
│   │   ├── config.py           # 參數配置 (複製自 config_template.py)
│   │   └── config_template.py  # 配置模板
│   ├── data/data_provider.py   # 數據獲取
│   ├── indicators/             # 技術指標
│   ├── strategy/               # 交易策略
│   ├── backtest/               # 回測引擎
│   └── utils/                  # 工具函數
├── batch_backtest.py           # 批量回測程式入口
├── reports/                    # 回測報告輸出
├── logs/                      # 日誌檔案
└── README.md                   # 專案說明
```

## ⚠️ 風險提醒

- 本程式僅供學習和研究使用
- 回測結果不代表未來表現
- 實際交易請謹慎評估風險
- 建議充分測試後再使用

## 📄 授權

本專案僅供學習和研究使用。
