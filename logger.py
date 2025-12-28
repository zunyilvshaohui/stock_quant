#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的日志系统
支持多处理器：控制台、文件、钉钉
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import threading

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
LOG_DIR = PROJECT_ROOT / "logs"


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    COLORS = {
        'DEBUG': '\033[94m',  # 蓝色
        'INFO': '\033[92m',  # 绿色
        'WARNING': '\033[93m',  # 黄色
        'ERROR': '\033[91m',  # 红色
        'CRITICAL': '\033[95m',  # 紫色
        'RESET': '\033[0m',  # 重置颜色
    }

    def format(self, record):
        # 保存原始日志级别
        original_levelname = record.levelname

        # 给日志级别添加颜色
        if original_levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[original_levelname]}{original_levelname}{self.COLORS['RESET']}"
            # 替换记录中的级别名称
            record.levelname = colored_levelname

            # 给消息添加颜色
            original_msg = record.getMessage()
            colored_msg = f"{self.COLORS[original_levelname]}{original_msg}{self.COLORS['RESET']}"
            record.msg = colored_msg

        result = super().format(record)

        # 恢复原始日志级别（避免影响后续处理）
        record.levelname = original_levelname

        return result


class DingTalkHandler(logging.Handler):
    """钉钉日志处理器"""

    def __init__(self, webhook_url: str = None, secret: str = None):
        super().__init__()
        self.webhook_url = webhook_url
        self.secret = secret
        self._lock = threading.Lock()

    def emit(self, record):
        """发送日志到钉钉"""
        try:
            import requests
            import json
            import hashlib
            import hmac
            import base64
            import urllib.parse
            import time

            # 只发送ERROR级别以上的日志
            if record.levelno < logging.ERROR:
                return

            # 构建消息
            message = {
                "msgtype": "text",
                "text": {
                    "content": f"🚨 系统告警\n"
                               f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                               f"级别: {record.levelname}\n"
                               f"模块: {record.name}\n"
                               f"消息: {record.getMessage()}\n"
                               f"文件: {record.pathname}:{record.lineno}"
                }
            }

            # 如果有异常信息，添加堆栈跟踪
            if record.exc_info:
                import traceback
                error_trace = traceback.format_exc()
                message["text"]["content"] += f"\n\n错误详情:\n{error_trace}"

            # 发送请求
            with self._lock:
                if self.webhook_url:
                    # 生成签名（如果提供了secret）
                    timestamp = int(time.time() * 1000)
                    sign = ""

                    if self.secret:
                        string_to_sign = f'{timestamp}\n{self.secret}'
                        hmac_code = hmac.new(
                            self.secret.encode('utf-8'),
                            string_to_sign.encode('utf-8'),
                            digestmod=hashlib.sha256
                        ).digest()
                        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

                    url = self.webhook_url
                    if sign:
                        url = f'{url}&timestamp={timestamp}&sign={sign}'

                    response = requests.post(
                        url,
                        json=message,
                        timeout=5
                    )

                    if response.status_code != 200:
                        print(f"钉钉消息发送失败: {response.status_code}")

        except Exception as e:
            # 避免递归错误
            print(f"钉钉处理器错误: {e}")


def setup_logger(
        name: str = "quant",
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_to_console: bool = True,
        dingtalk_config: Optional[Dict] = None
) -> logging.Logger:
    """
    设置并返回配置好的logger

    Args:
        name: logger名称
        log_level: 日志级别
        log_to_file: 是否记录到文件
        log_to_console: 是否输出到控制台
        dingtalk_config: 钉钉配置 {webhook, secret}

    Returns:
        logging.Logger: 配置好的logger实例
    """

    # 确保日志目录存在
    LOG_DIR.mkdir(exist_ok=True)

    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 控制台handler（带颜色）
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s [%(levelname)-8s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # 文件handler
    if log_to_file:
        # 主日志文件
        main_log_file = LOG_DIR / "quant_trading.log"
        file_handler = logging.FileHandler(main_log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)-8s] %(name)s %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 错误日志文件（只记录ERROR以上）
        error_log_file = LOG_DIR / "error.log"
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)

        # 交易日志文件
        trade_log_file = LOG_DIR / "trade.log"
        trade_handler = logging.FileHandler(trade_log_file, encoding='utf-8')
        trade_handler.setLevel(logging.INFO)
        trade_formatter = logging.Formatter(
            fmt='%(asctime)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        trade_handler.setFormatter(trade_formatter)

        # 创建专门的交易logger
        trade_logger = logging.getLogger("trade")
        trade_logger.setLevel(logging.INFO)
        trade_logger.addHandler(trade_handler)
        trade_logger.propagate = False

    # 钉钉handler（可选）
    if dingtalk_config and dingtalk_config.get('webhook'):
        dingtalk_handler = DingTalkHandler(
            webhook_url=dingtalk_config.get('webhook'),
            secret=dingtalk_config.get('secret')
        )
        dingtalk_handler.setLevel(logging.ERROR)
        logger.addHandler(dingtalk_handler)

    # 防止日志向上传播
    logger.propagate = False

    return logger


def get_logger(name: str = "quant") -> logging.Logger:
    """
    获取logger实例

    Args:
        name: logger名称

    Returns:
        logging.Logger: logger实例
    """
    logger = logging.getLogger(name)

    # 如果logger没有handler，使用默认配置
    if not logger.handlers:
        setup_logger(name)

    return logger


# 测试函数
def test_logger():
    """测试日志系统"""
    logger = get_logger("test")

    logger.debug("这是一条DEBUG消息")
    logger.info("这是一条INFO消息")
    logger.warning("这是一条WARNING消息")
    logger.error("这是一条ERROR消息")
    logger.critical("这是一条CRITICAL消息")

    # 测试交易日志
    trade_logger = logging.getLogger("trade")
    trade_logger.info("买入 000001.SZ 价格: 15.30 数量: 1000")
    trade_logger.info("卖出 000858.SZ 价格: 168.50 数量: 500")


if __name__ == "__main__":
    print("🧪 测试日志系统...")
    test_logger()
    print("✅ 日志系统测试完成")