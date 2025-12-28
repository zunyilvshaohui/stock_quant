# config/settings.py 文件内容
"""
全局系统设置
"""

import os
from pathlib import Path
from datetime import time

# 项目根路径
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
RESULTS_DIR = PROJECT_ROOT / "results"
CONFIG_DIR = PROJECT_ROOT / "config"

# 创建目录（如果不存在）
for directory in [DATA_DIR, LOG_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# 交易时间设置（A股）
TRADING_HOURS = {
    "pre_market": time(9, 15),      # 集合竞价开始
    "market_open": time(9, 30),     # 正式开盘
    "morning_close": time(11, 30),  # 上午收盘
    "afternoon_open": time(13, 0),  # 下午开盘
    "market_close": time(15, 0)     # 收盘
}

# 交易参数
TRADE_PARAMS = {
    "commission_rate": 0.0003,      # 佣金费率 0.03%
    "stamp_tax": 0.001,             # 印花税 0.1%
    "min_commission": 5.0,          # 最低佣金5元
    "min_trade_unit": 100,          # 最小交易单位（手）
    "slippage": 0.001               # 滑点率 0.1%
}

# 数据源配置
DATA_SOURCES = {
    "akshare": {
        "timeout": 30,
        "retry_times": 3
    },
    "tushare": {
        "token": "",  # 需要用户自己填写
        "timeout": 30
    }
}

# 策略默认参数
DEFAULT_STRATEGY_PARAMS = {
    "cci_strategy": {
        "period": 80,
        "base_threshold": 130,
        "calibration_days": 200,
        "time_decay_start": 20,
        "time_decay_rate": 0.01
    },
    "risk_management": {
        "max_position_ratio": 0.8,      # 最大仓位比例
        "stop_loss_pct": 0.05,          # 止损比例
        "take_profit_pct": 0.15,        # 止盈比例
        "max_daily_loss": 0.03          # 单日最大亏损
    }
}

# 日志文件路径
LOG_FILE_PATHS = {
    "main": LOG_DIR / "quant_trading.log",
    "trade": LOG_DIR / "trade_records.log",
    "error": LOG_DIR / "error.log"
}

# 全局常量
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# 系统状态码
STATUS_CODES = {
    "SUCCESS": 0,
    "ERROR": 1,
    "WARNING": 2,
    "NO_DATA": 3,
    "NETWORK_ERROR": 4
}

def get_project_root() -> Path:
    """获取项目根目录"""
    return PROJECT_ROOT

def get_data_dir() -> Path:
    """获取数据目录"""
    return DATA_DIR

def get_log_dir() -> Path:
    """获取日志目录"""
    return LOG_DIR

# 测试代码
if __name__ == "__main__":
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"数据目录: {DATA_DIR}")
    print(f"日志目录: {LOG_DIR}")
    print("配置加载完成！")