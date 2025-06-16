#!/usr/bin/env python3
"""
下單測試（含 OTOCO 委託示範）
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from macd_strategy.trading.trade_executor import TradeExecutor
from macd_strategy.core import config


def test_futures_otoco_order():
    """測試合約下單功能"""
    print("🚀 開始 OTOCO 委託測試")
    print("=" * 50)
    
    try:
        # 初始化交易執行器
        executor = TradeExecutor()
        
        # 顯示帳戶資訊
        balance = executor.get_account_balance()
        print(f"\n💰 帳戶餘額: ${balance:,.2f}")
        
        # 獲取當前價格
        price = executor.get_current_price()
        print(f"\n💵 當前價格: ${price:.2f}")
        
        # 顯示持倉資訊
        position = executor.get_position_info()
        if position:
            print(f"\n📊 當前持倉: {position}")
        else:
            print("\n📊 無持倉")
        
        # 計算倉位大小 (使用固定數量進行測試)
        quantity = config.POSITION_SIZE
        leverage = 1
        entry_price = 2625.5
        stop_loss = 2625
        take_profit = 2626
        side = 'BUY'
        
        print(f"\n📈 OTOCO下單數量: {quantity}, 槓桿: {leverage}, 進場價: {entry_price:.2f}, 止損: {stop_loss:.2f}, 止盈: {take_profit:.2f}")
        
        # 執行 OTOCO 做多委託
        print("\n📊 執行 OTOCO 做多委託")
        executor.place_otoco_order(side , quantity, entry_price, stop_loss, take_profit, leverage=leverage)
        
        print("\n✅ OTOCO 測試完成")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_futures_otoco_order() 