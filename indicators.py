#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标计算库
包含CCI、MACD、RSI、布林带等常用技术指标
重点实现动态CCI计算
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.absolute()
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import warnings

warnings.filterwarnings('ignore')

from utils.helpers import timer
from utils.logger import get_logger

logger = get_logger("indicators")


class TechnicalIndicators:
    """技术指标计算器"""

    def __init__(self, use_numpy: bool = True):
        """
        初始化技术指标计算器

        Args:
            use_numpy: 是否使用numpy加速计算
        """
        self.use_numpy = use_numpy
        logger.info("技术指标计算器初始化完成")

    @timer
    def calculate_cci(self, high: pd.Series, low: pd.Series, close: pd.Series,
                      period: int = 80) -> pd.Series:
        """
        计算CCI指标（商品通道指数）

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 计算周期

        Returns:
            pd.Series: CCI值
        """
        if len(close) < period:
            logger.warning(f"数据长度({len(close)})小于周期({period})，无法计算CCI")
            return pd.Series(index=close.index, dtype=float)

        logger.info(f"计算CCI指标，周期: {period}")

        # 使用手动循环计算以避免pandas rolling的问题
        cci_values = self._calculate_cci_manual(high.values, low.values,
                                                close.values, period)

        cci_series = pd.Series(cci_values, index=close.index)
        return cci_series

    def _calculate_cci_manual(self, high: np.ndarray, low: np.ndarray,
                              close: np.ndarray, period: int) -> np.ndarray:
        """
        手动计算CCI（使用numpy循环）

        Args:
            high: 最高价数组
            low: 最低价数组
            close: 收盘价数组
            period: 计算周期

        Returns:
            np.ndarray: CCI值数组
        """
        n = len(close)
        cci = np.full(n, np.nan, dtype=float)

        # 典型价格 = (最高 + 最低 + 收盘) / 3
        typical_price = (high + low + close) / 3.0

        for i in range(period - 1, n):
            start_idx = i - period + 1
            end_idx = i + 1

            # 计算典型价格的简单移动平均
            sma = np.mean(typical_price[start_idx:end_idx])

            # 计算平均偏差
            mean_deviation = np.mean(np.abs(typical_price[start_idx:end_idx] - sma))

            # 计算CCI
            if mean_deviation != 0:
                cci[i] = (typical_price[i] - sma) / (0.015 * mean_deviation)
            else:
                cci[i] = 0

        return cci

    @timer
    def calculate_dynamic_threshold(self, cci_values: pd.Series,
                                    base_threshold: float = 130,
                                    time_decay_start: int = 20,
                                    time_decay_rate: float = 0.01) -> pd.Series:
        """
        计算动态CCI阈值（随时间衰减）

        Args:
            cci_values: CCI值序列
            base_threshold: 基础阈值
            time_decay_start: 时间衰减开始周期
            time_decay_rate: 时间衰减率

        Returns:
            pd.Series: 动态阈值序列
        """
        if len(cci_values) == 0:
            return pd.Series(dtype=float)

        logger.info(f"计算动态CCI阈值，基础阈值: {base_threshold}")

        thresholds = np.full(len(cci_values), base_threshold, dtype=float)

        # 应用时间衰减
        for i in range(len(cci_values)):
            if i >= time_decay_start:
                # 衰减因子，最低衰减到0.7
                decay_factor = max(0.7, 1.0 - (i - time_decay_start) * time_decay_rate)
                thresholds[i] = base_threshold * decay_factor

        threshold_series = pd.Series(thresholds, index=cci_values.index)
        return threshold_series

    @timer
    def calculate_macd(self, close: pd.Series,
                       fast_period: int = 12,
                       slow_period: int = 26,
                       signal_period: int = 9) -> pd.DataFrame:
        """
        计算MACD指标

        Args:
            close: 收盘价序列
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期

        Returns:
            pd.DataFrame: 包含MACD、信号线、柱状图
        """
        if len(close) < slow_period + signal_period:
            logger.warning("数据长度不足，无法计算MACD")
            return pd.DataFrame()

        logger.info(f"计算MACD指标，参数: {fast_period}/{slow_period}/{signal_period}")

        # 计算EMA
        ema_fast = close.ewm(span=fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=slow_period, adjust=False).mean()

        # 计算DIF（差离值）
        dif = ema_fast - ema_slow

        # 计算DEA（信号线）
        dea = dif.ewm(span=signal_period, adjust=False).mean()

        # 计算MACD柱状图
        macd_hist = (dif - dea) * 2

        result = pd.DataFrame({
            'DIF': dif,
            'DEA': dea,
            'MACD': macd_hist
        })

        return result

    @timer
    def calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """
        计算RSI指标（相对强弱指数）

        Args:
            close: 收盘价序列
            period: 计算周期

        Returns:
            pd.Series: RSI值
        """
        if len(close) < period + 1:
            logger.warning(f"数据长度({len(close)})不足，无法计算RSI")
            return pd.Series(index=close.index, dtype=float)

        logger.info(f"计算RSI指标，周期: {period}")

        # 计算价格变化
        delta = close.diff()

        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 计算平均上涨和平均下跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # 计算RS
        rs = avg_gain / (avg_loss + 1e-8)  # 避免除零

        # 计算RSI
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @timer
    def calculate_bollinger_bands(self, close: pd.Series,
                                  period: int = 20,
                                  num_std: float = 2.0) -> pd.DataFrame:
        """
        计算布林带

        Args:
            close: 收盘价序列
            period: 移动平均周期
            num_std: 标准差倍数

        Returns:
            pd.DataFrame: 包含中轨、上轨、下轨
        """
        if len(close) < period:
            logger.warning(f"数据长度({len(close)})不足，无法计算布林带")
            return pd.DataFrame()

        logger.info(f"计算布林带，周期: {period}, 标准差倍数: {num_std}")

        # 计算中轨（移动平均）
        middle_band = close.rolling(window=period).mean()

        # 计算标准差
        std = close.rolling(window=period).std()

        # 计算上轨和下轨
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)

        result = pd.DataFrame({
            'upper': upper_band,
            'middle': middle_band,
            'lower': lower_band
        })

        return result

    @timer
    def calculate_atr(self, high: pd.Series, low: pd.Series,
                      close: pd.Series, period: int = 14) -> pd.Series:
        """
        计算ATR指标（平均真实波幅）

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 计算周期

        Returns:
            pd.Series: ATR值
        """
        if len(close) < period + 1:
            logger.warning(f"数据长度({len(close)})不足，无法计算ATR")
            return pd.Series(index=close.index, dtype=float)

        logger.info(f"计算ATR指标，周期: {period}")

        # 计算真实波幅
        high_low = high - low
        high_close_prev = np.abs(high - close.shift(1))
        low_close_prev = np.abs(low - close.shift(1))

        # 真实波幅 = max(当日高低差, |当日最高-前日收盘|, |当日最低-前日收盘|)
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1)
        true_range = true_range.max(axis=1)

        # 计算ATR（平均真实波幅）
        atr = true_range.rolling(window=period).mean()

        return atr

    @timer
    def calculate_position_sizing(self, account_value: float,
                                  risk_per_trade: float = 0.02,
                                  stop_loss_pct: float = 0.05,
                                  current_price: float = None) -> Dict:
        """
        基于风险计算仓位大小

        Args:
            account_value: 账户总值
            risk_per_trade: 单笔交易风险比例（默认2%）
            stop_loss_pct: 止损比例（默认5%）
            current_price: 当前价格

        Returns:
            Dict: 包含仓位信息的字典
        """
        # 计算风险金额
        risk_amount = account_value * risk_per_trade

        # 计算止损金额
        stop_loss_amount = risk_amount / stop_loss_pct if stop_loss_pct > 0 else 0

        result = {
            'account_value': account_value,
            'risk_per_trade': risk_per_trade,
            'risk_amount': risk_amount,
            'stop_loss_pct': stop_loss_pct,
            'stop_loss_amount': stop_loss_amount,
        }

        if current_price is not None and current_price > 0:
            # 计算可买入股数（假设交易单位100股）
            shares = int(stop_loss_amount / current_price / 100) * 100
            position_value = shares * current_price

            result.update({
                'current_price': current_price,
                'shares': shares,
                'position_value': position_value,
                'position_pct': position_value / account_value if account_value > 0 else 0
            })

        logger.debug(f"仓位计算: 账户{account_value:.2f}, 风险金额{risk_amount:.2f}")
        return result

    @timer
    def calculate_all_indicators(self, df: pd.DataFrame,
                                 config: Dict = None) -> pd.DataFrame:
        """
        计算所有技术指标

        Args:
            df: 价格数据（必须包含open, high, low, close, volume）
            config: 指标配置

        Returns:
            pd.DataFrame: 包含所有指标的数据
        """
        if df.empty:
            return df

        # 默认配置
        if config is None:
            config = {
                'cci_period': 80,
                'rsi_period': 14,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'bollinger_period': 20,
                'bollinger_std': 2.0,
                'atr_period': 14
            }

        logger.info("开始计算所有技术指标")
        df_indicators = df.copy()

        # 确保有必要的列
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df_indicators.columns for col in required_cols):
            logger.error(f"数据缺少必要列，需要: {required_cols}")
            return df_indicators

        # 1. 计算CCI
        cci = self.calculate_cci(
            df_indicators['high'],
            df_indicators['low'],
            df_indicators['close'],
            period=config.get('cci_period', 80)
        )
        df_indicators['CCI'] = cci

        # 2. 计算动态CCI阈值
        if 'CCI' in df_indicators.columns:
            dynamic_threshold = self.calculate_dynamic_threshold(
                df_indicators['CCI'],
                base_threshold=130,
                time_decay_start=20,
                time_decay_rate=0.01
            )
            df_indicators['CCI_Threshold'] = dynamic_threshold

        # 3. 计算MACD
        macd_result = self.calculate_macd(
            df_indicators['close'],
            fast_period=config.get('macd_fast', 12),
            slow_period=config.get('macd_slow', 26),
            signal_period=config.get('macd_signal', 9)
        )
        if not macd_result.empty:
            df_indicators = pd.concat([df_indicators, macd_result], axis=1)

        # 4. 计算RSI
        rsi = self.calculate_rsi(
            df_indicators['close'],
            period=config.get('rsi_period', 14)
        )
        df_indicators['RSI'] = rsi

        # 5. 计算布林带
        bollinger_result = self.calculate_bollinger_bands(
            df_indicators['close'],
            period=config.get('bollinger_period', 20),
            num_std=config.get('bollinger_std', 2.0)
        )
        if not bollinger_result.empty:
            df_indicators = pd.concat([df_indicators, bollinger_result], axis=1)

        # 6. 计算ATR
        atr = self.calculate_atr(
            df_indicators['high'],
            df_indicators['low'],
            df_indicators['close'],
            period=config.get('atr_period', 14)
        )
        df_indicators['ATR'] = atr

        # 7. 计算价格变化率
        df_indicators['returns'] = df_indicators['close'].pct_change()

        # 8. 计算移动平均线
        df_indicators['MA5'] = df_indicators['close'].rolling(window=5).mean()
        df_indicators['MA20'] = df_indicators['close'].rolling(window=20).mean()
        df_indicators['MA60'] = df_indicators['close'].rolling(window=60).mean()

        logger.info(f"指标计算完成，总列数: {len(df_indicators.columns)}")
        return df_indicators

    def detect_signals(self, df: pd.DataFrame,
                       indicator_config: Dict = None) -> pd.DataFrame:
        """
        基于技术指标检测交易信号

        Args:
            df: 包含技术指标的数据
            indicator_config: 指标配置

        Returns:
            pd.DataFrame: 包含信号标记的数据
        """
        if df.empty or 'CCI' not in df.columns:
            return df

        df_signals = df.copy()

        # CCI信号
        if 'CCI' in df_signals.columns:
            # 金叉信号：CCI上穿0轴
            df_signals['CCI_cross_up'] = (df_signals['CCI'] > 0) & (df_signals['CCI'].shift(1) <= 0)

            # 死叉信号：CCI下穿0轴
            df_signals['CCI_cross_down'] = (df_signals['CCI'] < 0) & (df_signals['CCI'].shift(1) >= 0)

            # 超买信号：CCI超过阈值
            if 'CCI_Threshold' in df_signals.columns:
                df_signals['CCI_overbought'] = df_signals['CCI'] > df_signals['CCI_Threshold']
                df_signals['CCI_oversold'] = df_signals['CCI'] < -df_signals['CCI_Threshold']

        # MACD信号
        if 'DIF' in df_signals.columns and 'DEA' in df_signals.columns:
            # 金叉：DIF上穿DEA
            df_signals['MACD_golden_cross'] = (df_signals['DIF'] > df_signals['DEA']) & \
                                              (df_signals['DIF'].shift(1) <= df_signals['DEA'].shift(1))

            # 死叉：DIF下穿DEA
            df_signals['MACD_dead_cross'] = (df_signals['DIF'] < df_signals['DEA']) & \
                                            (df_signals['DIF'].shift(1) >= df_signals['DEA'].shift(1))

        # RSI信号
        if 'RSI' in df_signals.columns:
            # 超买超卖
            df_signals['RSI_overbought'] = df_signals['RSI'] > 70
            df_signals['RSI_oversold'] = df_signals['RSI'] < 30

        # 价格位置信号
        if all(col in df_signals.columns for col in ['close', 'MA20']):
            df_signals['price_above_MA20'] = df_signals['close'] > df_signals['MA20']
            df_signals['price_below_MA20'] = df_signals['close'] < df_signals['MA20']

        logger.info(f"信号检测完成，检测到 {df_signals.filter(like='cross').sum().sum()} 个交叉信号")
        return df_signals


# 测试函数
def test_indicators():
    """测试技术指标计算"""
    print("🧪 测试技术指标计算...")

    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", end="2024-03-31", freq='B')
    n_days = len(dates)

    # 生成模拟价格序列（随机游走）
    returns = np.random.normal(0.0005, 0.02, n_days)
    price_series = 100 * (1 + returns).cumprod()

    test_data = pd.DataFrame({
        'open': price_series * (1 + np.random.normal(0, 0.01, n_days)),
        'high': price_series * (1 + np.abs(np.random.normal(0.01, 0.015, n_days))),
        'low': price_series * (1 - np.abs(np.random.normal(0.01, 0.015, n_days))),
        'close': price_series,
        'volume': np.random.randint(1000000, 50000000, n_days)
    }, index=dates)

    print(f"测试数据: {len(test_data)} 条记录")

    # 创建指标计算器
    indicators = TechnicalIndicators()

    # 测试单个指标计算
    print("\n1. 测试CCI计算...")
    cci = indicators.calculate_cci(
        test_data['high'],
        test_data['low'],
        test_data['close'],
        period=80
    )
    print(f"   CCI计算完成，有效值: {cci.notna().sum()}")
    print(f"   CCI范围: [{cci.min():.2f}, {cci.max():.2f}]")

    # 测试动态阈值
    print("\n2. 测试动态CCI阈值...")
    thresholds = indicators.calculate_dynamic_threshold(cci)
    print(f"   阈值范围: [{thresholds.min():.2f}, {thresholds.max():.2f}]")

    # 测试MACD
    print("\n3. 测试MACD计算...")
    macd_result = indicators.calculate_macd(test_data['close'])
    print(f"   MACD计算完成，列数: {len(macd_result.columns)}")

    # 测试RSI
    print("\n4. 测试RSI计算...")
    rsi = indicators.calculate_rsi(test_data['close'])
    print(f"   RSI范围: [{rsi.min():.2f}, {rsi.max():.2f}]")

    # 测试布林带
    print("\n5. 测试布林带计算...")
    bollinger = indicators.calculate_bollinger_bands(test_data['close'])
    print(f"   布林带计算完成")

    # 测试所有指标
    print("\n6. 测试所有指标计算...")
    all_indicators = indicators.calculate_all_indicators(test_data)
    print(f"   所有指标计算完成，总列数: {len(all_indicators.columns)}")
    print(f"   新增指标列: {[col for col in all_indicators.columns if col not in test_data.columns][:10]}")

    # 测试信号检测
    print("\n7. 测试信号检测...")
    signals = indicators.detect_signals(all_indicators)
    signal_cols = [col for col in signals.columns if 'cross' in col or 'over' in col]
    print(f"   信号检测完成，信号列: {signal_cols}")

    # 测试仓位计算
    print("\n8. 测试仓位计算...")
    position_info = indicators.calculate_position_sizing(
        account_value=1000000,
        risk_per_trade=0.02,
        stop_loss_pct=0.05,
        current_price=test_data['close'].iloc[-1]
    )
    print(f"   仓位计算结果:")
    for key, value in position_info.items():
        if isinstance(value, float):
            print(f"     {key}: {value:.2f}")
        else:
            print(f"     {key}: {value}")

    print("\n✅ 技术指标测试完成")
    return all_indicators


if __name__ == "__main__":
    test_indicators()