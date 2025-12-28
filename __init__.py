#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块 - 提供各种辅助函数和工具类
"""

# 导出核心工具类
from .logger import setup_logger, get_logger
from .helpers import timer, retry, Singleton
from .date_utils import is_trading_day, get_next_trading_day
from .notifier import Notifier, DingTalkNotifier

# 版本信息
__version__ = "1.0.0"
__author__ = "股票量化策略团队"
__description__ = "量化交易工具模块"

# 导出列表
__all__ = [
    # 日志
    "setup_logger",
    "get_logger",

    # 辅助函数
    "timer",
    "retry",
    "Singleton",

    # 日期工具
    "is_trading_day",
    "get_next_trading_day",

    # 通知
    "Notifier",
    "DingTalkNotifier",

    # 装饰器
    "timer",
    "retry",
]

# 初始化信息
print(f"📦 工具模块 v{__version__} 已加载")