# MACD 短線交易策略

基於 MACD 指標的短線交易策略，支持實時監控、回測分析和動態槓桿管理。

## ✨ 主要功能

- **實時信號監控**：每小時檢查交易信號，支持無限循環監控
- **回測分析**：歷史數據回測驗證策略效果
- **動態槓桿管理**：根據幣安分級制度自動調整槓桿倍數
- **資產變化圖表**：視覺化回測結果和總資產變化
- **風險管理**：內建停損停利、每日虧損限制機制
- **多時間框架**：結合1小時和4小時MACD確認信號

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 配置參數

編輯 `src/macd_strategy/core/config.py`：

```python
# 交易對和交易所配置
SYMBOL = "ETHUSDT"
EXCHANGE = "binance"

# 回測配置
BACKTEST_DAYS = 360
WARMUP_DAYS = 30

# MACD 指標參數
MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 9

# 信號確認參數
MIN_CONSECUTIVE_BARS = 5

# 風險管理參數
STOP_LOSS_MULTIPLIER = 2.0
RISK_REWARD_RATIO = 1.1
RISK_PER_TRADE = 0.02
POSITION_SIZE = 0.1
LEVERAGE = 100  # 期望槓桿，實際會根據持倉價值動態調整
```

### 3. 執行程序

#### 方式一：使用主選單（推薦）

```bash
# 啟動主程序，提供互動式選單
python main.py
```

#### 方式二：直接執行特定功能

```bash
# 執行回測
python backtest.py
python backtest.py --initial_capital 50000 --days 180

# 啟動實時監控
python monitor.py
python monitor.py --initial_capital 10000

# 批量回測分析
python batch.py
python batch.py --initial_capital 50000
```

#### 方式三：使用模組執行（進階）

```bash
# 回測
python -m src.macd_strategy.backtest.backtest_engine --initial_capital 10000

# 監控
python -m src.macd_strategy.strategy.trading_strategy
```

## 🔧 動態槓桿系統

### 幣安ETHUSDT槓桿分級制度

| 名義持倉價值 | 最大槓桿 | 維持保證金率 | 維持保證金額度 |
|-------------|---------|-------------|---------------|
| $0 - $50,000 | 125x | 0.40% | $0 |
| $50,000 - $600,000 | 100x | 0.50% | $50 |
| $600,000 - $3,000,000 | 75x | 0.65% | $950 |
| $3,000,000 - $12,000,000 | 50x | 1.00% | $11,450 |
| $12,000,000 - $50,000,000 | 25x | 2.00% | $131,450 |

### 動態調整邏輯

1. **自動槓桿限制**：根據持倉價值自動調整到允許的最大槓桿
2. **維持保證金計算**：使用對應級別的維持保證金比率
3. **爆倉價格計算**：基於幣安實際公式計算爆倉價格
4. **風險透明化**：每筆交易顯示實際槓桿和級別信息

### 槓桿受限示例

```
📥 做多進場 - 價格: $2500.00 ⚠️ 槓桿受限 (100x → 75x)
💰 倉位大小: 300.0000 ETH (名義價值 $750,000.00, 75x 槓桿)
🔧 槓桿級別: $600,000 - $3,000,000, 最大槓桿: 75x, 維持保證金率: 0.65%
```

## 📈 策略邏輯

### 做多信號條件
1. 1小時MACD直方圖從負轉正（第一根轉正）
2. 轉正前至少有5根連續負值直方圖
3. 4小時MACD直方圖為正值（趨勢確認）

### 做空信號條件
1. 1小時MACD直方圖從正轉負（第一根轉負）
2. 轉負前至少有5根連續正值直方圖  
3. 4小時MACD直方圖為負值（趨勢確認）

### 風險管理
- **停損**：ATR × 2.0
- **停利**：ATR × 2.0 × 1.1（風險報酬比1:1.1）
- **每日虧損限制**：5%（可配置）
- **動態槓桿**：根據持倉價值自動調整
- **倉位管理**：10%資金作為保證金

## 📊 回測與圖表功能

### 回測輸出

回測完成後會自動生成：

1. **詳細交易報告**：包含每筆交易的槓桿詳情
2. **資產變化圖表**：視覺化總資產變化
3. **績效統計**：勝率、平均損益、最大回撤等
4. **槓桿分析**：顯示槓桿受限情況

### 圖表功能特色

- **雙圖表設計**：
  - 上圖：總資產變化曲線 vs 買入持有基準
  - 下圖：價格走勢與交易點標記
- **交易點標記**：
  - 綠色三角：做多進場/做空停利
  - 紅色倒三角：做空進場/做多停利
  - 顏色區分盈虧結果
- **統計信息**：顯示關鍵績效指標
- **自動保存**：圖表保存至 `logs/` 資料夾

## 📁 項目結構

```
MACD_S/
├── src/macd_strategy/
│   ├── core/
│   │   ├── config.py              # 主要配置文件
│   │   └── leverage_calculator.py # 動態槓桿計算器
│   ├── data/
│   │   └── data_provider.py       # 數據獲取模組
│   ├── indicators/
│   │   └── technical_indicators.py # 技術指標計算
│   ├── strategy/
│   │   └── trading_strategy.py     # 交易策略邏輯
│   └── backtest/
│       └── backtest_engine.py      # 回測引擎
├── logs/                          # 日誌與圖表輸出
│   ├── *.txt                     # 交易日誌文件
│   └── *.png                     # 回測圖表文件
├── test_leverage.py              # 槓桿功能測試
├── analyze_leverage_progression.py # 槓桿分析工具
├── requirements.txt              # 依賴套件
└── README.md                    # 說明文件
```

## ⚙️ 配置說明

### 主要參數

| 參數 | 說明 | 建議值 |
|------|------|--------|
| `MACD_FAST` | 快線EMA週期 | 6 |
| `MACD_SLOW` | 慢線EMA週期 | 13 |
| `MACD_SIGNAL` | 信號線EMA週期 | 9 |
| `MIN_CONSECUTIVE_BARS` | 最少連續直方圖數量 | 5 |
| `STOP_LOSS_MULTIPLIER` | 停損倍數 | 2.0 |
| `RISK_REWARD_RATIO` | 風險報酬比 | 1.1 |
| `POSITION_SIZE` | 倉位大小比例 | 0.1 (10%) |
| `LEVERAGE` | 期望槓桿倍數 | 100 |

### 風險管理配置

```python
RISK_CONFIG = {
    'MAX_DAILY_LOSS': 0.05,  # 每日最大虧損5%
    'MAX_DRAWDOWN': 0.20     # 最大回撤20%（配置項）
}
```

## 🔧 依賴套件

- `pandas>=1.5.0` - 數據處理
- `numpy>=1.21.0` - 數值計算
- `matplotlib>=3.5.0` - 圖表繪製
- `requests>=2.28.0` - API請求
- `ta>=0.10.2` - 技術指標
- `python-binance>=1.0.19` - 幣安API

## 📊 回測結果示例

### 回測報告內容

回測完成後會顯示詳細的績效分析，包括：

- **基本信息**：回測期間、初始/最終資金、總報酬率
- **交易統計**：總交易次數、獲利/虧損交易數、勝率
- **績效指標**：平均損益、最佳/最差交易、獲利因子
- **基準比較**：與買入持有策略的比較
- **槓桿分析**：動態槓桿調整情況
- **風險指標**：最大回撤、每日虧損統計

### 輸出文件說明

- **圖表文件**：`logs/backtest_equity_curve_[SYMBOL]_[TIMESTAMP].png`
- **交易日誌**：`logs/trading_log.txt`
- **回測日誌**：`logs/backtest_log.txt`
- **監控日誌**：`logs/monitoring_log.txt`

## 🛠️ 進階功能

### 1. 自定義初始資金

```bash
# 不同資金規模測試
python -m src.macd_strategy.backtest.backtest_engine --initial_capital 1000   # 小資
python -m src.macd_strategy.backtest.backtest_engine --initial_capital 100000 # 大戶
```

### 2. 槓桿分析工具

```bash
# 查看不同資金規模的槓桿限制
python test_leverage.py

# 分析槓桿受限的具體原因
python analyze_leverage_progression.py
```

### 3. 監控模式

實時監控會：
- 每小時檢查信號（在每小時的01秒執行）
- 自動記錄所有檢查結果
- 僅在發現信號時發出提醒
- 支持無限循環運行

## 📝 注意事項

1. **僅供學習研究**：本策略僅用於教育目的，實際交易風險自負
2. **動態槓桿**：系統會根據持倉價值自動調整槓桿，這是正常的風險控制機制
3. **資金管理**：建議從小額開始測試，逐步增加資金規模
4. **網絡連接**：實時監控需要穩定的網絡連接以獲取數據
5. **API限制**：注意幣安API的請求頻率限制

## 🎯 策略優勢

- ✅ **真實交易環境模擬**：完全按照幣安規則執行
- ✅ **智能風險控制**：動態槓桿防止過度風險
- ✅ **高度透明化**：每筆交易詳情一目了然
- ✅ **專業級回測**：包含完整的績效分析
- ✅ **易於使用**：簡單的命令行界面

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request 來改進這個項目！

## 📄 授權

MIT License
