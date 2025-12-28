#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心策略模块
包含数据获取、指标计算、策略实现等核心功能
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "股票量化策略团队"
__description__ = "量化策略核心模块"

# 导出核心类
from .data_fetcher import DataFetcher
from .data_processor import DataProcessor
from .indicators import TechnicalIndicators
from .base_strategy import BaseStrategy

# 尝试导入DynamicCCIStrategy（如果存在）
try:
    from .strategy import DynamicCCIStrategy

    __all__.append("DynamicCCIStrategy")
except ImportError:
    print("⚠️  DynamicCCIStrategy暂不可用，将在第4天创建")
    DynamicCCIStrategy = None

# 导出列表
__all__ = [
    # 数据模块
    "DataFetcher",
    "DataProcessor",

    # 指标模块
    "TechnicalIndicators",

    # 策略模块
    "BaseStrategy",
]

print(f"📦 核心模块 v{__version__} 已加载")