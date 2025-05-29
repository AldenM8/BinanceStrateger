# MACD 交易策略專案結構說明

## 📁 專案架構

簡化後的專案結構，專注於核心功能：正式運行和回測。

### 🏗️ 目錄結構

```
MACD_S/
├── src/                          # 源代碼目錄
│   └── macd_strategy/           # 主要策略包
│       ├── __init__.py          # 策略包初始化
│       ├── core/                # 核心配置模組
│       │   ├── __init__.py
│       │   └── config.py        # 策略參數配置
│       ├── data/                # 數據獲取模組
│       │   ├── __init__.py
│       │   └── data_provider.py # Binance API 數據獲取
│       ├── indicators/          # 技術指標模組
│       │   ├── __init__.py
│       │   └── technical_indicators.py # MACD、ATR 計算
│       ├── strategy/            # 交易策略模組
│       │   ├── __init__.py
│       │   └── trading_strategy.py # 核心交易邏輯
│       ├── backtest/            # 回測引擎模組
│       │   ├── __init__.py
│       │   └── backtest_engine.py # 回測執行引擎
│       └── utils/               # 工具函數模組
│           ├── __init__.py
│           ├── validators.py    # 數據驗證
│           └── formatters.py    # 格式化工具
├── docs/                        # 文檔目錄
│   └── PROJECT_STRUCTURE.md    # 專案結構說明
├── logs/                        # 日誌目錄
│   └── trading_log.txt         # 交易日誌
├── data/                        # 數據目錄（預留）
├── main.py                      # 主程式入口
├── setup.py                     # 安裝腳本
├── .gitignore                   # Git 忽略文件
├── README.md                    # 專案說明
└── requirements.txt             # 依賴套件
```

## 🔧 核心功能

### 1. 回測功能
- **執行**: `python main.py`
- **配置**: 編輯 `src/macd_strategy/core/config.py`
- **報告**: 自動生成詳細回測報告

### 2. 實時交易策略
- **監控**: 24/7 市場監控
- **信號**: MACD 轉折信號檢測
- **風控**: 自動停損停利

## ⚙️ 配置參數

編輯 `src/macd_strategy/core/config.py`:

```python
# MACD 參數
MACD_FAST = 6       # 快線週期
MACD_SLOW = 13      # 慢線週期  
MACD_SIGNAL = 9     # 信號線週期

# 風險管理
STOP_LOSS_MULTIPLIER = 2.0    # 停損倍數
RISK_REWARD_RATIO = 3.0       # 風報比
POSITION_SIZE = 0.1           # 倉位大小(10%)

# 回測設定
BACKTEST_DAYS = 30           # 回測天數
WARMUP_DAYS = 600            # 預熱天數
```

## 🚀 快速開始

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行回測
python main.py
```

## 📊 使用範例

```python
from src.macd_strategy.backtest.backtest_engine import run_backtest

# 自定義回測
results = run_backtest(
    symbol='SOLUSDT',
    days=30,
    initial_capital=10000.0
)
```

---

*專注核心功能：回測與實時交易策略* 