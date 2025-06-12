#!/usr/bin/env python3
"""
測試動態槓桿功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.macd_strategy.core.leverage_calculator import LeverageCalculator
from src.macd_strategy.core import config

def test_leverage_brackets():
    """測試槓桿分級功能"""
    print("🔧 幣安ETHUSDT槓桿分級制度測試")
    print("=" * 70)
    
    # 測試不同持倉價值
    test_values = [
        5000,      # $5K - 125x槓桿
        25000,     # $25K - 125x槓桿
        100000,    # $100K - 100x槓桿
        500000,    # $500K - 100x槓桿
        1000000,   # $1M - 75x槓桿
        5000000,   # $5M - 50x槓桿
        15000000,  # $15M - 25x槓桿
        60000000,  # $60M - 20x槓桿
        100000000, # $100M - 10x槓桿
        200000000  # $200M - 5x槓桿
    ]
    
    for value in test_values:
        bracket = LeverageCalculator.get_leverage_bracket(value)
        max_lev = LeverageCalculator.calculate_max_leverage(value)
        mmr = LeverageCalculator.calculate_maintenance_margin_rate(value)
        
        print(f"持倉價值: ${value:>12,}")
        print(f"  最大槓桿: {max_lev:>3}x")
        print(f"  維持保證金率: {mmr*100:>5.2f}%")
        print(f"  維持保證金額度: ${bracket['maintenance_amount']:>10,.0f}")
        print()

def test_position_calculation():
    """測試倉位計算功能"""
    print("💰 動態槓桿倉位計算測試")
    print("=" * 70)
    
    # 測試參數
    capital = 10000  # $10K 初始資金
    position_size_ratio = 0.1  # 10% 倉位
    desired_leverage = 100  # 期望100x槓桿
    entry_prices = [3000, 3500, 4000]  # 不同進場價格
    
    for price in entry_prices:
        print(f"進場價格: ${price}")
        
        details = LeverageCalculator.calculate_position_details(
            capital=capital,
            position_size_ratio=position_size_ratio,
            desired_leverage=desired_leverage,
            entry_price=price
        )
        
        print(f"  保證金占用: ${details['margin_used']:>8.2f}")
        print(f"  期望槓桿: {details['desired_leverage']:>3}x")
        print(f"  實際槓桿: {details['actual_leverage']:>3}x")
        print(f"  名義價值: ${details['actual_notional']:>10.2f}")
        print(f"  持倉數量: {details['position_quantity']:>10.4f} ETH")
        print(f"  維持保證金率: {details['maintenance_margin_rate']*100:>5.2f}%")
        print(f"  維持保證金: ${details['maintenance_margin']:>8.2f}")
        
        if details['leverage_limited']:
            print(f"  ⚠️ 槓桿受限: {desired_leverage}x → {details['actual_leverage']}x")
        else:
            print(f"  ✅ 槓桿無限制")
        
        # 計算爆倉價格
        liq_long = LeverageCalculator.calculate_liquidation_price(price, details, is_long=True)
        liq_short = LeverageCalculator.calculate_liquidation_price(price, details, is_long=False)
        
        print(f"  做多爆倉價: ${liq_long:>8.2f}")
        print(f"  做空爆倉價: ${liq_short:>8.2f}")
        print()

def test_leverage_scaling():
    """測試槓桿縮放情況"""
    print("📊 槓桿縮放場景測試")
    print("=" * 70)
    
    # 模擬不同資金規模的用戶
    test_scenarios = [
        {"capital": 1000, "name": "小資用戶"},
        {"capital": 10000, "name": "一般用戶"},
        {"capital": 100000, "name": "大戶"},
        {"capital": 1000000, "name": "機構用戶"}
    ]
    
    entry_price = 3500
    position_ratio = 0.5  # 50% 倉位（較激進）
    
    for scenario in test_scenarios:
        capital = scenario["capital"]
        name = scenario["name"]
        
        print(f"{name} (資金: ${capital:,})")
        
        details = LeverageCalculator.calculate_position_details(
            capital=capital,
            position_size_ratio=position_ratio,
            desired_leverage=100,
            entry_price=entry_price
        )
        
        margin = details['margin_used']
        notional = details['actual_notional']
        leverage = details['actual_leverage']
        
        print(f"  保證金: ${margin:>10.2f} ({position_ratio*100}% 倉位)")
        print(f"  名義價值: ${notional:>10.2f}")
        print(f"  實際槓桿: {leverage:>3}x")
        print(f"  {LeverageCalculator.get_leverage_info_summary(notional)}")
        
        if details['leverage_limited']:
            print(f"  ⚠️ 槓桿受限制")
        else:
            print(f"  ✅ 槓桿無限制")
        print()

def main():
    """主函數"""
    print("🚀 動態槓桿系統測試")
    print("=" * 70)
    print(f"測試交易對: {config.SYMBOL}")
    print(f"配置槓桿: {config.LEVERAGE}x")
    print(f"倉位大小: {config.POSITION_SIZE*100}%")
    print()
    
    # 執行各項測試
    test_leverage_brackets()
    test_position_calculation()
    test_leverage_scaling()
    
    print("✅ 動態槓桿系統測試完成！")

if __name__ == "__main__":
    main() 