"""
幣安槓桿計算器
根據持倉價值動態計算可用槓桿和維持保證金比率
"""

from typing import Dict, Tuple
from . import config


class LeverageCalculator:
    """幣安槓桿分級計算器"""
    
    @staticmethod
    def get_leverage_bracket(notional_value: float) -> Dict:
        """
        根據名義持倉價值獲取對應的槓桿級別
        
        Args:
            notional_value: 名義持倉價值 (USDT)
            
        Returns:
            對應的槓桿級別字典
        """
        for bracket in config.BINANCE_LEVERAGE_BRACKETS:
            if bracket["notional_min"] <= notional_value < bracket["notional_max"]:
                return bracket
        
        # 如果超過最大範圍，使用最後一個級別
        return config.BINANCE_LEVERAGE_BRACKETS[-1]
    
    @staticmethod
    def calculate_max_leverage(notional_value: float) -> int:
        """
        計算指定持倉價值下的最大槓桿倍數
        
        Args:
            notional_value: 名義持倉價值 (USDT)
            
        Returns:
            最大槓桿倍數
        """
        bracket = LeverageCalculator.get_leverage_bracket(notional_value)
        return bracket["max_leverage"]
    
    @staticmethod
    def calculate_maintenance_margin_rate(notional_value: float) -> float:
        """
        計算指定持倉價值下的維持保證金比率
        
        Args:
            notional_value: 名義持倉價值 (USDT)
            
        Returns:
            維持保證金比率 (小數形式)
        """
        bracket = LeverageCalculator.get_leverage_bracket(notional_value)
        return bracket["maintenance_margin_rate"]
    
    @staticmethod
    def calculate_optimal_leverage(desired_leverage: int, notional_value: float) -> int:
        """
        計算最優槓桿倍數（不超過幣安限制）
        
        Args:
            desired_leverage: 期望的槓桿倍數
            notional_value: 名義持倉價值 (USDT)
            
        Returns:
            實際可用的槓桿倍數
        """
        max_leverage = LeverageCalculator.calculate_max_leverage(notional_value)
        return min(desired_leverage, max_leverage)
    
    @staticmethod
    def calculate_position_details(capital: float, position_size_ratio: float, 
                                 desired_leverage: int, entry_price: float) -> Dict:
        """
        計算完整的持倉詳情（包含槓桿限制）
        
        Args:
            capital: 可用資金 (USDT)
            position_size_ratio: 倉位大小比率 (如 0.1 = 10%)
            desired_leverage: 期望槓桿倍數
            entry_price: 進場價格
            
        Returns:
            持倉詳情字典
        """
        # 計算初始保證金
        margin_used = capital * position_size_ratio
        
        # 計算初始名義價值（使用期望槓桿）
        initial_notional = margin_used * desired_leverage
        
        # 檢查槓桿限制
        actual_leverage = LeverageCalculator.calculate_optimal_leverage(
            desired_leverage, initial_notional
        )
        
        # 重新計算實際名義價值
        actual_notional = margin_used * actual_leverage
        
        # 計算持倉數量
        position_quantity = actual_notional / entry_price
        
        # 獲取對應的槓桿級別信息
        bracket = LeverageCalculator.get_leverage_bracket(actual_notional)
        
        # 計算維持保證金
        maintenance_margin = (actual_notional * bracket["maintenance_margin_rate"] 
                            - bracket["maintenance_amount"])
        
        return {
            "margin_used": margin_used,
            "actual_leverage": actual_leverage,
            "desired_leverage": desired_leverage,
            "actual_notional": actual_notional,
            "position_quantity": position_quantity,
            "maintenance_margin_rate": bracket["maintenance_margin_rate"],
            "maintenance_margin": maintenance_margin,
            "leverage_bracket": bracket,
            "leverage_limited": actual_leverage < desired_leverage
        }
    
    @staticmethod
    def calculate_liquidation_price(entry_price: float, position_details: Dict, 
                                  is_long: bool = True) -> float:
        """
        計算爆倉價格（使用幣安公式）
        
        Args:
            entry_price: 進場價格
            position_details: 持倉詳情（來自 calculate_position_details）
            is_long: 是否為多單
            
        Returns:
            爆倉價格
        """
        notional = position_details["actual_notional"]
        margin = position_details["margin_used"]
        mmr = position_details["maintenance_margin_rate"]
        mma = position_details["leverage_bracket"]["maintenance_amount"]
        
        # 幣安爆倉價格公式
        # 多單爆倉價格 = (WB - MMA) / (PS × (MMR - 1))
        # 空單爆倉價格 = (WB - MMA) / (PS × (MMR + 1))
        # 其中：WB = 錢包餘額 + 未實現損益, PS = 持倉數量, MMR = 維持保證金比率, MMA = 維持保證金額度
        
        position_size = position_details["position_quantity"]
        wallet_balance = margin  # 簡化：假設錢包餘額等於保證金
        
        if is_long:
            # 做多爆倉價格
            liquidation_price = (wallet_balance - mma) / (position_size * (mmr - 1))
        else:
            # 做空爆倉價格  
            liquidation_price = (wallet_balance - mma) / (position_size * (mmr + 1))
        
        return max(0, liquidation_price)  # 確保價格不為負數
    
    @staticmethod
    def get_leverage_info_summary(notional_value: float) -> str:
        """
        獲取槓桿信息摘要（用於日誌顯示）
        
        Args:
            notional_value: 名義持倉價值 (USDT)
            
        Returns:
            格式化的槓桿信息字串
        """
        bracket = LeverageCalculator.get_leverage_bracket(notional_value)
        
        return (f"槓桿級別: ${bracket['notional_min']:,} - ${bracket['notional_max']:,}, "
                f"最大槓桿: {bracket['max_leverage']}x, "
                f"維持保證金率: {bracket['maintenance_margin_rate']*100:.2f}%") 