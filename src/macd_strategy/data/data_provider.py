"""
Binance 數據提供者
使用 Binance API 作為數據源獲取 K 線數據
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import warnings
import requests
import time

from ..core import config

# 設定台灣時區 (UTC+8)
TAIWAN_TZ = timezone(timedelta(hours=8))

# Binance API 時間間隔對應
BINANCE_INTERVALS = {
    '1m': '1m',
    '3m': '3m',
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1h': '1h',
    '2h': '2h',
    '4h': '4h',
    '6h': '6h',
    '8h': '8h',
    '12h': '12h',
    '1d': '1d',
    '3d': '3d',
    '1w': '1w',
    '1M': '1M'
}


class BinanceDataProvider:
    """Binance 數據提供者"""
    
    def __init__(self):
        """初始化數據提供者"""
        self.base_url = "https://api.binance.com"
        self.name = "Binance"
        
    def get_ohlcv_data(self, symbol: str, interval: str, n_bars: int = 1000) -> Optional[pd.DataFrame]:
        """
        獲取 OHLCV 數據
        
        Args:
            symbol: 交易對符號 (如 'SOLUSDT')
            interval: 時間間隔 ('1h', '4h', '1d' 等)
            n_bars: 獲取的K線數量 (最大1000)
        
        Returns:
            包含 OHLCV 數據的 DataFrame，索引為時間戳
        """
        
        try:
            # 檢查時間間隔
            if interval not in BINANCE_INTERVALS:
                print(f"❌ 不支援的時間間隔: {interval}")
                print(f"支援的時間間隔: {list(BINANCE_INTERVALS.keys())}")
                return None
            
            # 限制數據量
            limit = min(n_bars, 1000)  # Binance API 限制
            
            # 建立 API 請求
            endpoint = "/api/v3/klines"
            params = {
                'symbol': symbol.upper(),
                'interval': BINANCE_INTERVALS[interval],
                'limit': limit
            }
            
            # 發送請求
            url = self.base_url + endpoint
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Binance API 請求失敗: {response.status_code}")
                return None
            
            data = response.json()
            
            if not data:
                print(f"❌ 沒有獲取到 {symbol} 的數據")
                return None
            
            # 轉換為 DataFrame
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                      'close_time', 'quote_volume', 'count', 'taker_buy_volume',
                      'taker_buy_quote_volume', 'ignore']
            
            df = pd.DataFrame(data, columns=columns)
            
            # 只保留必要的欄位
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # 轉換數據類型
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 設定時間索引
            df.set_index('timestamp', inplace=True)
            
            # 確保時間索引為 UTC
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            
            # 移除無效數據
            df = df.dropna()
            
            # 按時間排序
            df = df.sort_index()
            
            return df
            
        except Exception as e:
            print(f"❌ 獲取數據時發生錯誤: {e}")
            return None


# 全域數據提供者實例
_data_provider = BinanceDataProvider()


def get_binance_data(symbol: str, interval: str, n_bars: int = 1000) -> Optional[pd.DataFrame]:
    """
    快捷函數：獲取 Binance 數據
    
    Args:
        symbol: 交易對符號 (如 'SOLUSDT')
        interval: 時間間隔
        n_bars: 獲取的K線數量
    
    Returns:
        包含 OHLCV 數據的 DataFrame
    """
    return _data_provider.get_ohlcv_data(symbol, interval, n_bars)


def get_binance_klines(symbol: str, interval: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    獲取指定日期範圍的 K 線數據（支援大量歷史數據）
    
    Args:
        symbol: 交易對符號
        interval: 時間間隔
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)
    
    Returns:
        K 線數據 DataFrame
    """
    try:
        # 轉換日期為時間戳
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 轉換為毫秒時間戳
        start_ts = int(start_dt.timestamp() * 1000)
        end_ts = int(end_dt.timestamp() * 1000)
        
        all_data = []
        current_start = start_ts
        
        print(f"📡 獲取 {symbol} {interval} 數據範圍: {start_date} 到 {end_date}")
        
        while current_start < end_ts:
            try:
                # 建立 API 請求
                endpoint = "/api/v3/klines"
                params = {
                    'symbol': symbol.upper(),
                    'interval': BINANCE_INTERVALS[interval],
                    'startTime': current_start,
                    'endTime': end_ts,
                    'limit': 1000  # Binance API 單次最大限制
                }
                
                # 發送請求
                url = "https://api.binance.com" + endpoint
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code != 200:
                    print(f"❌ Binance API 請求失敗: {response.status_code}")
                    break
                
                data = response.json()
                
                if not data:
                    print(f"⚠️  沒有更多數據可獲取")
                    break
                
                all_data.extend(data)
                
                # 更新下一批的開始時間（最後一筆數據的時間 + 1毫秒）
                last_timestamp = data[-1][0]
                current_start = last_timestamp + 1
                
                print(f"   已獲取 {len(data)} 筆數據，總計 {len(all_data)} 筆")
                
                # 如果返回的數據少於1000筆，表示已經獲取完畢
                if len(data) < 1000:
                    break
                
                # 避免請求過於頻繁
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 獲取數據批次失敗: {e}")
                break
        
        if not all_data:
            print(f"❌ 沒有獲取到 {symbol} 的數據")
            return None
        
        # 轉換為 DataFrame
        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                  'close_time', 'quote_volume', 'count', 'taker_buy_volume',
                  'taker_buy_quote_volume', 'ignore']
        
        df = pd.DataFrame(all_data, columns=columns)
        
        # 只保留必要的欄位
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        # 轉換數據類型
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 設定時間索引
        df.set_index('timestamp', inplace=True)
        
        # 確保時間索引為 UTC
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        
        # 移除重複數據
        df = df[~df.index.duplicated(keep='first')]
        
        # 移除無效數據
        df = df.dropna()
        
        # 按時間排序
        df = df.sort_index()
        
        # 過濾到指定的日期範圍
        start_filter = pd.Timestamp(start_dt, tz='UTC')
        end_filter = pd.Timestamp(end_dt, tz='UTC')
        df = df[(df.index >= start_filter) & (df.index <= end_filter)]
        
        print(f"✅ 成功獲取 {len(df)} 筆 {symbol} {interval} 數據")
        
        return df
        
    except Exception as e:
        print(f"❌ 獲取歷史數據失敗: {e}")
        return None


# 為了向後兼容，提供 DataProvider 類別
class DataProvider:
    """向後兼容的數據提供者介面"""
    
    def __init__(self, exchange: str = None):
        self.provider = _data_provider
        self.exchange = exchange or "binance"
    
    def get_ohlcv_data(self, symbol: str, interval: str, n_bars: int = 1000) -> Optional[pd.DataFrame]:
        """獲取 OHLCV 數據"""
        return self.provider.get_ohlcv_data(symbol, interval, n_bars)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        獲取當前價格
        
        Args:
            symbol: 交易對符號
            
        Returns:
            當前價格或 None
        """
        try:
            # 獲取最新的1分鐘K線作為當前價格
            data = self.provider.get_ohlcv_data(symbol, '1m', 1)
            if data is not None and len(data) > 0:
                return float(data['close'].iloc[-1])
            return None
        except Exception as e:
            print(f"❌ 獲取當前價格失敗: {e}")
            return None




def format_taiwan_time(timestamp):
    """將時間戳轉換為台灣時間字串"""
    if pd.isna(timestamp):
        return "N/A"
    
    # 確保是 datetime 對象
    if isinstance(timestamp, str):
        timestamp = pd.to_datetime(timestamp)
    
    # 轉換為台灣時間
    if timestamp.tz is None:
        # 假設是 UTC 時間
        taiwan_time = timestamp.replace(tzinfo=timezone.utc).astimezone(TAIWAN_TZ)
    else:
        taiwan_time = timestamp.astimezone(TAIWAN_TZ)
    
    return taiwan_time.strftime('%Y-%m-%d %H:%M:%S')


def test_data_connection():
    """測試數據連接"""
    print("🔍 測試 Binance API 數據連接...")
    
    try:
        # 導入配置以獲取測試交易對
        try:
            from ..core import config
            test_symbol = config.SYMBOL
        except ImportError:
            from src.macd_strategy.core import config
            test_symbol = config.SYMBOL
        
        # 測試獲取配置中的交易對數據
        data = get_binance_data(test_symbol, '1h', 10)
        
        if data is not None and len(data) > 0:
            print(f"✅ 成功獲取 {len(data)} 筆 {test_symbol} 1小時數據")
            print(f"   時間範圍: {format_taiwan_time(data.index[0])} 到 {format_taiwan_time(data.index[-1])}")
            print(f"   價格範圍: ${data['low'].min():.2f} - ${data['high'].max():.2f}")
            return True
        else:
            print("❌ 無法獲取數據")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


if __name__ == "__main__":
    test_data_connection() 