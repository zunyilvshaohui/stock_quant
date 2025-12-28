#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略基类 - 所有交易策略的父类
定义策略的标准接口和通用功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.absolute()
sys.path.insert(0, str(project_root))

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date
import pandas as pd
import numpy as np

from utils.logger import get_logger
from utils.helpers import timer
from utils.notifier import Notifier
from config import global_config

logger = get_logger("base_strategy")


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str, config: Optional[Dict] = None,
                 notifier: Optional[Notifier] = None):
        """
        初始化策略基类

        Args:
            name: 策略名称
            config: 策略配置
            notifier: 通知器
        """
        self.name = name
        self.config = config or {}
        self.notifier = notifier

        # 策略状态
        self.initialized = False
        self.running = False
        self.position = 0  # 当前持仓数量
        self.cash = 0.0  # 现金
        self.total_value = 0.0  # 总资产

        # 交易记录
        self.trade_history = []
        self.signal_history = []

        # 性能指标
        self.total_return = 0.0
        self.max_drawdown = 0.0
        self.win_rate = 0.0
        self.total_trades = 0

        logger.info(f"策略基类初始化: {name}")

    def initialize(self, initial_capital: float = 1000000.0) -> bool:
        """
        初始化策略

        Args:
            initial_capital: 初始资金

        Returns:
            bool: 是否初始化成功
        """
        try:
            self.cash = initial_capital
            self.total_value = initial_capital
            self.position = 0

            self.initialized = True
            logger.info(f"策略 {self.name} 初始化完成，初始资金: {initial_capital:.2f}")

            # 发送初始化通知
            if self.notifier:
                self.notifier.send(
                    f"策略 {self.name} 初始化完成\n初始资金: ¥{initial_capital:,.2f}",
                    level="info"
                )

            return True

        except Exception as e:
            logger.error(f"策略初始化失败: {e}")
            return False

    @abstractmethod
    def on_bar(self, bar_data: Dict) -> Dict:
        """
        处理新的K线数据（子类必须实现）

        Args:
            bar_data: K线数据，包含:
                - symbol: 标的代码
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - date: 日期

        Returns:
            Dict: 交易信号，包含:
                - action: 操作 (BUY/SELL/HOLD)
                - symbol: 标的
                - price: 价格
                - quantity: 数量
                - reason: 信号原因
        """
        pass

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标（子类必须实现）

        Args:
            data: 价格数据

        Returns:
            pd.DataFrame: 包含技术指标的数据
        """
        pass

    def generate_signal(self, current_data: Dict,
                        indicators: Dict) -> Dict:
        """
        生成交易信号（模板方法，子类可重写）

        Args:
            current_data: 当前数据
            indicators: 技术指标

        Returns:
            Dict: 交易信号
        """
        # 默认实现：没有信号
        return {
            'action': 'HOLD',
            'symbol': current_data.get('symbol', ''),
            'price': current_data.get('close', 0),
            'quantity': 0,
            'reason': '无信号',
            'timestamp': datetime.now()
        }

    def check_risk(self, signal: Dict) -> bool:
        """
        检查交易风险

        Args:
            signal: 交易信号

        Returns:
            bool: 是否通过风险检查
        """
        if signal['action'] == 'HOLD':
            return True

        # 检查价格有效性
        price = signal.get('price', 0)
        if price <= 0:
            logger.warning(f"价格无效: {price}")
            return False

        # 检查数量有效性
        quantity = signal.get('quantity', 0)
        if quantity <= 0:
            logger.warning(f"数量无效: {quantity}")
            return False

        # 检查资金是否足够（对于买入）
        if signal['action'] == 'BUY':
            cost = price * quantity
            if cost > self.cash * 0.95:  # 保留5%现金
                logger.warning(f"资金不足: 需要{cost:.2f}, 可用{self.cash:.2f}")
                return False

        # 检查持仓是否足够（对于卖出）
        if signal['action'] == 'SELL' and quantity > self.position:
            logger.warning(f"持仓不足: 需要卖出{quantity}, 当前持仓{self.position}")
            return False

        return True

    def execute_trade(self, signal: Dict) -> Dict:
        """
        执行交易

        Args:
            signal: 交易信号

        Returns:
            Dict: 交易结果
        """
        if not self.check_risk(signal):
            return {
                'success': False,
                'reason': '风险检查未通过',
                'signal': signal
            }

        try:
            action = signal['action']
            symbol = signal['symbol']
            price = signal['price']
            quantity = signal['quantity']
            reason = signal.get('reason', '')

            # 计算交易金额
            trade_amount = price * quantity

            # 更新账户
            if action == 'BUY':
                self.position += quantity
                self.cash -= trade_amount
                logger.info(f"买入 {symbol}: {quantity}股 @ {price:.2f}, 金额: {trade_amount:.2f}")

            elif action == 'SELL':
                self.position -= quantity
                self.cash += trade_amount
                logger.info(f"卖出 {symbol}: {quantity}股 @ {price:.2f}, 金额: {trade_amount:.2f}")

            # 更新总资产（按当前价格估算）
            self.total_value = self.cash + (self.position * price if self.position > 0 else 0)

            # 记录交易
            trade_record = {
                'timestamp': datetime.now(),
                'action': action,
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'amount': trade_amount,
                'reason': reason,
                'position': self.position,
                'cash': self.cash,
                'total_value': self.total_value
            }

            self.trade_history.append(trade_record)
            self.total_trades += 1

            # 发送交易通知
            if self.notifier:
                trade_data = {
                    'symbol': symbol,
                    'action': action,
                    'price': price,
                    'quantity': quantity,
                    'amount': trade_amount,
                    'reason': reason
                }
                self.notifier.send_trade_signal(trade_data)

            # 记录信号
            self.signal_history.append(signal)

            return {
                'success': True,
                'trade_record': trade_record,
                'signal': signal
            }

        except Exception as e:
            logger.error(f"交易执行失败: {e}")
            return {
                'success': False,
                'reason': str(e),
                'signal': signal
            }

    def update_position_value(self, current_price: float) -> None:
        """
        更新持仓市值

        Args:
            current_price: 当前价格
        """
        if self.position > 0:
            position_value = self.position * current_price
            self.total_value = self.cash + position_value

    def get_account_summary(self) -> Dict:
        """
        获取账户摘要

        Returns:
            Dict: 账户信息
        """
        return {
            'strategy': self.name,
            'timestamp': datetime.now(),
            'position': self.position,
            'cash': self.cash,
            'total_value': self.total_value,
            'total_trades': self.total_trades,
            'total_return': self.total_return,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate
        }

    def calculate_performance(self) -> Dict:
        """
        计算策略性能指标

        Returns:
            Dict: 性能指标
        """
        if not self.trade_history:
            return {}

        # 提取交易记录
        trades = pd.DataFrame(self.trade_history)

        if trades.empty:
            return {}

        # 计算盈亏
        buy_trades = trades[trades['action'] == 'BUY']
        sell_trades = trades[trades['action'] == 'SELL']

        # 计算胜率（简化版）
        if len(sell_trades) > 0:
            # 这里需要更复杂的盈亏计算
            self.win_rate = 0.5  # 简化

        # 计算总收益
        initial_value = 1000000.0  # 假设初始资金
        if self.total_value > 0:
            self.total_return = (self.total_value - initial_value) / initial_value

        return {
            'total_return': self.total_return,
            'annual_return': self.total_return,  # 简化
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'sharpe_ratio': 0.0,  # 简化
            'profit_factor': 0.0  # 简化
        }

    def get_trade_history(self, limit: int = None) -> List[Dict]:
        """
        获取交易历史

        Args:
            limit: 限制返回的记录数

        Returns:
            List[Dict]: 交易记录列表
        """
        if limit is None:
            return self.trade_history
        else:
            return self.trade_history[-limit:]

    def get_signal_history(self, limit: int = None) -> List[Dict]:
        """
        获取信号历史

        Args:
            limit: 限制返回的记录数

        Returns:
            List[Dict]: 信号记录列表
        """
        if limit is None:
            return self.signal_history
        else:
            return self.signal_history[-limit:]

    def reset(self) -> None:
        """重置策略状态"""
        self.position = 0
        self.cash = 0
        self.total_value = 0
        self.trade_history = []
        self.signal_history = []
        self.total_trades = 0
        self.total_return = 0.0
        self.max_drawdown = 0.0
        self.win_rate = 0.0

        self.initialized = False
        self.running = False

        logger.info(f"策略 {self.name} 已重置")

    def stop(self) -> None:
        """停止策略"""
        self.running = False
        logger.info(f"策略 {self.name} 已停止")

        # 发送停止通知
        if self.notifier:
            summary = self.get_account_summary()
            message = f"策略 {self.name} 已停止\n" \
                      f"总资产: ¥{summary['total_value']:,.2f}\n" \
                      f"总交易: {summary['total_trades']}笔\n" \
                      f"总收益: {summary['total_return'] * 100:.2f}%"
            self.notifier.send(message, level="info")

    def run_backtest(self, data: pd.DataFrame,
                     initial_capital: float = 1000000.0) -> Dict:
        """
        运行回测（简化版）

        Args:
            data: 历史数据
            initial_capital: 初始资金

        Returns:
            Dict: 回测结果
        """
        logger.info(f"开始回测策略: {self.name}")

        # 初始化
        if not self.initialized:
            self.initialize(initial_capital)

        self.running = True

        # 计算技术指标
        data_with_indicators = self.calculate_indicators(data)

        # 遍历每个交易日
        for idx, row in data_with_indicators.iterrows():
            if not self.running:
                break

            # 准备bar数据
            bar_data = {
                'symbol': self.config.get('symbol', '000001.SZ'),
                'date': idx,
                'open': row.get('open', 0),
                'high': row.get('high', 0),
                'low': row.get('low', 0),
                'close': row.get('close', 0),
                'volume': row.get('volume', 0)
            }

            # 获取指标
            indicators = {col: row[col] for col in data_with_indicators.columns
                          if col not in ['open', 'high', 'low', 'close', 'volume']}

            # 生成信号
            signal = self.generate_signal(bar_data, indicators)

            # 如果信号不是HOLD，执行交易
            if signal['action'] != 'HOLD':
                self.execute_trade(signal)

            # 更新持仓市值
            self.update_position_value(bar_data['close'])

        # 计算性能
        performance = self.calculate_performance()

        logger.info(f"回测完成: {self.name}")
        logger.info(f"最终资产: {self.total_value:.2f}")
        logger.info(f"总收益: {performance.get('total_return', 0) * 100:.2f}%")

        return {
            'strategy_name': self.name,
            'initial_capital': initial_capital,
            'final_value': self.total_value,
            'performance': performance,
            'trade_history': self.trade_history,
            'signal_history': self.signal_history
        }

    def generate_report(self) -> Dict:
        """
        生成策略报告

        Returns:
            Dict: 策略报告
        """
        summary = self.get_account_summary()
        performance = self.calculate_performance()

        report = {
            'strategy_info': {
                'name': self.name,
                'config': self.config,
                'initialized': self.initialized,
                'running': self.running
            },
            'account_summary': summary,
            'performance': performance,
            'trade_statistics': {
                'total_trades': len(self.trade_history),
                'buy_trades': len([t for t in self.trade_history if t['action'] == 'BUY']),
                'sell_trades': len([t for t in self.trade_history if t['action'] == 'SELL']),
                'last_trade': self.trade_history[-1] if self.trade_history else None
            },
            'timestamp': datetime.now()
        }

        return report


# 简单策略示例（用于测试）
class SimpleMovingAverageStrategy(BaseStrategy):
    """简单移动平均策略示例"""

    def __init__(self, config: Optional[Dict] = None,
                 notifier: Optional[Notifier] = None):
        super().__init__("SimpleMA", config, notifier)

        # 策略参数
        self.fast_period = config.get('fast_period', 5) if config else 5
        self.slow_period = config.get('slow_period', 20) if config else 20

        logger.info(f"简单移动平均策略初始化，参数: {self.fast_period}/{self.slow_period}")

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算移动平均线"""
        data_indicators = data.copy()

        # 计算快速和慢速移动平均
        data_indicators['MA_fast'] = data_indicators['close'].rolling(window=self.fast_period).mean()
        data_indicators['MA_slow'] = data_indicators['close'].rolling(window=self.slow_period).mean()

        return data_indicators

    def on_bar(self, bar_data: Dict) -> Dict:
        """处理K线数据"""
        # 这里应该使用实时数据，但在回测中我们会用run_backtest方法
        return self.generate_signal(bar_data, {})

    def generate_signal(self, current_data: Dict, indicators: Dict) -> Dict:
        """生成交易信号"""
        # 在实际使用中，indicators应该包含计算好的指标
        # 这里简化处理

        price = current_data.get('close', 0)

        # 模拟信号生成逻辑
        signal = {
            'action': 'HOLD',
            'symbol': current_data.get('symbol', ''),
            'price': price,
            'quantity': 0,
            'reason': '无信号',
            'timestamp': datetime.now()
        }

        # 简单示例：价格涨就买，跌就卖
        # 实际策略需要更复杂的逻辑

        return signal


# 测试函数
def test_base_strategy():
    """测试策略基类"""
    print("🧪 测试策略基类...")

    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq='B')
    n_days = len(dates)

    price_series = 100 + np.cumsum(np.random.randn(n_days))

    test_data = pd.DataFrame({
        'open': price_series,
        'high': price_series + np.random.rand(n_days) * 2,
        'low': price_series - np.random.rand(n_days) * 2,
        'close': price_series,
        'volume': np.random.randint(1000000, 50000000, n_days)
    }, index=dates)

    print(f"测试数据: {len(test_data)} 条记录")

    # 测试简单策略
    print("\n1. 测试简单移动平均策略...")

    strategy_config = {
        'symbol': '000001.SZ',
        'fast_period': 5,
        'slow_period': 20
    }

    simple_strategy = SimpleMovingAverageStrategy(config=strategy_config)

    # 初始化策略
    print("   初始化策略...")
    success = simple_strategy.initialize(initial_capital=1000000)
    print(f"   初始化结果: {success}")

    # 获取账户摘要
    print("   获取账户摘要...")
    summary = simple_strategy.get_account_summary()
    for key, value in summary.items():
        if isinstance(value, (int, float)):
            print(f"     {key}: {value}")

    # 测试回测
    print("\n2. 测试回测功能...")
    backtest_result = simple_strategy.run_backtest(
        data=test_data,
        initial_capital=1000000
    )

    print(f"   回测完成，最终资产: {backtest_result['final_value']:.2f}")
    print(f"   总交易次数: {len(backtest_result['trade_history'])}")

    # 测试性能计算
    print("\n3. 测试性能计算...")
    performance = simple_strategy.calculate_performance()
    print(f"   性能指标:")
    for key, value in performance.items():
        if isinstance(value, (int, float)):
            print(f"     {key}: {value:.4f}")

    # 测试报告生成
    print("\n4. 测试报告生成...")
    report = simple_strategy.generate_report()
    print(f"   报告生成完成，包含 {len(report)} 个部分")

    # 测试重置
    print("\n5. 测试策略重置...")
    simple_strategy.reset()
    summary_after_reset = simple_strategy.get_account_summary()
    print(f"   重置后账户: {summary_after_reset['total_value']:.2f}")

    print("\n✅ 策略基类测试完成")
    return backtest_result


if __name__ == "__main__":
    test_base_strategy()