# MACD 短線交易策略

基於 MACD 指標的短線交易策略，支持實時監控、回測分析和自動化交易。

## ✨ 主要功能

- **實時信號監控**：每小時檢查交易信號
- **回測分析**：歷史數據回測驗證策略效果
- **資產變化圖表**：視覺化回測結果和總資產變化
- **風險管理**：內建停損停利機制
- **多時間框架**：結合1小時和4小時MACD確認信號

## 📊 回測與圖表功能

### 運行帶圖表的回測

```bash
# 運行回測並生成資產變化圖表
python backtest_with_chart.py
```

這將：
1. 執行完整的回測分析
2. 生成總資產變化折線圖
3. 顯示買入持有基準線對比
4. 標記所有交易進出場點
5. 自動保存圖表為PNG文件到logs資料夾

### 圖表功能特色

- **雙圖表設計**：
  - 上圖：總資產變化曲線 vs 買入持有基準
  - 下圖：價格走勢與交易點標記
- **交易點標記**：
  - 綠色三角：做多進場/做空停利
  - 紅色倒三角：做空進場/做多停利
  - 顏色區分盈虧結果
- **統計信息**：顯示關鍵績效指標
- **中文界面**：完整的繁體中文支持

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
BACKTEST_DAYS = 30

# MACD 指標參數
MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 9

# 信號確認參數
MIN_CONSECUTIVE_BARS = 5
```

### 3. 執行回測（含圖表）

```bash
python backtest_with_chart.py
```

### 4. 實時信號監控

```bash
python -m src.macd_strategy.strategy.trading_strategy
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
- 停損：ATR × 2.0
- 停利：ATR × 2.0 × 1.1（風險報酬比1:1.1）
- 槓桿：100倍（可調整）
- 倉位：10%資金作為保證金

## 📁 項目結構

```
MACD_S/
├── src/macd_strategy/
│   ├── core/           # 配置文件
│   ├── data/           # 數據獲取模組
│   ├── indicators/     # 技術指標計算
│   ├── strategy/       # 交易策略邏輯
│   └── backtest/       # 回測引擎
├── logs/               # 日誌與圖表輸出
│   ├── *.txt          # 交易日誌文件
│   └── *.png          # 回測圖表文件
├── backtest_with_chart.py  # 帶圖表的回測腳本
├── requirements.txt    # 依賴套件
└── README.md          # 說明文件
```

## ⚙️ 配置說明

### 主要參數

| 參數 | 說明 | 建議值 |
|------|------|--------|
| `MACD_FAST` | 快線EMA週期 | 6-15 |
| `MACD_SLOW` | 慢線EMA週期 | 13-30 |
| `MACD_SIGNAL` | 信號線EMA週期 | 9-12 |
| `MIN_CONSECUTIVE_BARS` | 最少連續直方圖數量 | 3-6 |
| `STOP_LOSS_MULTIPLIER` | 停損倍數 | 1.5-3.0 |
| `RISK_REWARD_RATIO` | 風險報酬比 | 1.0-2.0 |

## 🔧 依賴套件

- `pandas>=1.5.0` - 數據處理
- `numpy>=1.21.0` - 數值計算
- `matplotlib>=3.5.0` - 圖表繪製
- `requests>=2.28.0` - API請求
- `ta>=0.10.2` - 技術指標
- `python-binance>=1.0.19` - 幣安API

## 📝 注意事項

1. **僅供學習研究**：本策略僅用於教育目的，實際交易風險自負
2. **參數調整**：建議根據不同市場條件調整參數
3. **風險控制**：務必設定合理的停損機制
4. **資金管理**：建議小額測試，控制倉位風險

## 📊 回測結果示例

運行回測後將在`logs/`資料夾中生成包含以下信息的圖表：
- 總資產變化曲線
- 買入持有基準對比
- 交易進出場點標記
- 關鍵績效統計數據
- 價格走勢分析

### 輸出文件說明

- **圖表文件**：`logs/backtest_equity_curve_[SYMBOL]_[TIMESTAMP].png`
- **交易日誌**：`logs/trading_log.txt`
- **回測日誌**：`logs/backtest_log.txt`

所有輸出文件都會集中保存在`logs/`資料夾中，方便管理和查看。

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request 來改進這個項目！

## 📄 授權

MIT License
