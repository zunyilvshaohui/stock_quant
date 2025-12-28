#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日期时间工具模块
专门处理交易日计算、时间转换等
"""

import datetime
from datetime import date, datetime, timedelta
from typing import List, Optional, Union
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
import pytz


class TradingCalendar:
    """交易日历类"""

    # A股节假日（示例，需要更新）
    HOLIDAYS = {
        # 2023年
        2023: [
            date(2023, 1, 1),  # 元旦
            date(2023, 1, 2),
            date(2023, 1, 21),  # 春节
            date(2023, 1, 22),
            date(2023, 1, 23),
            date(2023, 1, 24),
            date(2023, 1, 25),
            date(2023, 1, 26),
            date(2023, 1, 27),
            date(2023, 4, 5),  # 清明
            date(2023, 4, 29),  # 劳动节
            date(2023, 4, 30),
            date(2023, 5, 1),
            date(2023, 5, 2),
            date(2023, 5, 3),
            date(2023, 6, 22),  # 端午
            date(2023, 6, 23),
            date(2023, 6, 24),
            date(2023, 9, 29),  # 中秋国庆
            date(2023, 9, 30),
            date(2023, 10, 1),
            date(2023, 10, 2),
            date(2023, 10, 3),
            date(2023, 10, 4),
            date(2023, 10, 5),
            date(2023, 10, 6),
        ],
        # 2024年
        2024: [
            date(2024, 1, 1),  # 元旦
            date(2024, 2, 10),  # 春节
            date(2024, 2, 11),
            date(2024, 2, 12),
            date(2024, 2, 13),
            date(2024, 2, 14),
            date(2024, 2, 15),
            date(2024, 2, 16),
            date(2024, 2, 17),
            date(2024, 4, 4),  # 清明
            date(2024, 4, 5),
            date(2024, 4, 6),
            date(2024, 5, 1),  # 劳动节
            date(2024, 5, 2),
            date(2024, 5, 3),
            date(2024, 5, 4),
            date(2024, 5, 5),
            date(2024, 6, 8),  # 端午
            date(2024, 6, 9),
            date(2024, 6, 10),
            date(2024, 9, 15),  # 中秋
            date(2024, 9, 16),
            date(2024, 9, 17),
            date(2024, 10, 1),  # 国庆
            date(2024, 10, 2),
            date(2024, 10, 3),
            date(2024, 10, 4),
            date(2024, 10, 5),
            date(2024, 10, 6),
            date(2024, 10, 7),
        ]
    }

    @classmethod
    def is_holiday(cls, check_date: Union[date, datetime, str]) -> bool:
        """
        判断是否为节假日

        Args:
            check_date: 检查的日期

        Returns:
            bool: 是否为节假日
        """
        # 转换为date对象
        if isinstance(check_date, str):
            check_date = datetime.strptime(check_date, "%Y-%m-%d").date()
        elif isinstance(check_date, datetime):
            check_date = check_date.date()

        # 检查是否为周末
        if check_date.weekday() >= 5:  # 5=周六, 6=周日
            return True

        # 检查是否为节假日
        year = check_date.year
        if year in cls.HOLIDAYS:
            return check_date in cls.HOLIDAYS[year]

        return False

    @classmethod
    def is_trading_day(cls, check_date: Union[date, datetime, str]) -> bool:
        """
        判断是否为交易日

        Args:
            check_date: 检查的日期

        Returns:
            bool: 是否为交易日
        """
        return not cls.is_holiday(check_date)

    @classmethod
    def get_next_trading_day(cls, start_date: Union[date, datetime, str],
                             n: int = 1) -> date:
        """
        获取第n个交易日

        Args:
            start_date: 起始日期
            n: 第几个交易日（n=1表示下一个交易日）

        Returns:
            date: 第n个交易日
        """
        # 转换为date对象
        if isinstance(start_date, str):
            current_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            current_date = start_date.date()
        else:
            current_date = start_date

        count = 0
        while count < n:
            current_date += timedelta(days=1)
            if cls.is_trading_day(current_date):
                count += 1

        return current_date

    @classmethod
    def get_previous_trading_day(cls, start_date: Union[date, datetime, str],
                                 n: int = 1) -> date:
        """
        获取前第n个交易日

        Args:
            start_date: 起始日期
            n: 第几个交易日（n=1表示上一个交易日）

        Returns:
            date: 前第n个交易日
        """
        # 转换为date对象
        if isinstance(start_date, str):
            current_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            current_date = start_date.date()
        else:
            current_date = start_date

        count = 0
        while count < n:
            current_date -= timedelta(days=1)
            if cls.is_trading_day(current_date):
                count += 1

        return current_date

    @classmethod
    def get_trading_days_between(cls, start_date: Union[date, datetime, str],
                                 end_date: Union[date, datetime, str]) -> List[date]:
        """
        获取两个日期之间的所有交易日

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[date]: 交易日列表
        """
        # 转换为date对象
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()

        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        elif isinstance(end_date, datetime):
            end_date = end_date.date()

        trading_days = []
        current_date = start_date

        while current_date <= end_date:
            if cls.is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)

        return trading_days

    @classmethod
    def get_trading_days_count(cls, start_date: Union[date, datetime, str],
                               end_date: Union[date, datetime, str]) -> int:
        """
        计算两个日期之间的交易日数量

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            int: 交易日数量
        """
        trading_days = cls.get_trading_days_between(start_date, end_date)
        return len(trading_days)


def is_trading_day(check_date: Union[date, datetime, str]) -> bool:
    """
    判断是否为交易日（快捷函数）

    Args:
        check_date: 检查的日期

    Returns:
        bool: 是否为交易日
    """
    return TradingCalendar.is_trading_day(check_date)


def get_next_trading_day(start_date: Union[date, datetime, str],
                         n: int = 1) -> date:
    """
    获取第n个交易日（快捷函数）

    Args:
        start_date: 起始日期
        n: 第几个交易日

    Returns:
        date: 第n个交易日
    """
    return TradingCalendar.get_next_trading_day(start_date, n)


def get_previous_trading_day(start_date: Union[date, datetime, str],
                             n: int = 1) -> date:
    """
    获取前第n个交易日（快捷函数）

    Args:
        start_date: 起始日期
        n: 第几个交易日

    Returns:
        date: 前第n个交易日
    """
    return TradingCalendar.get_previous_trading_day(start_date, n)


def get_trading_days_between(start_date: Union[date, datetime, str],
                             end_date: Union[date, datetime, str]) -> List[date]:
    """
    获取两个日期之间的所有交易日（快捷函数）

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        List[date]: 交易日列表
    """
    return TradingCalendar.get_trading_days_between(start_date, end_date)


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime:
    """
    解析日期字符串

    Args:
        date_str: 日期字符串
        fmt: 日期格式

    Returns:
        datetime: 解析后的datetime对象
    """
    return datetime.strptime(date_str, fmt)


def format_date(date_obj: Union[date, datetime],
                fmt: str = "%Y-%m-%d") -> str:
    """
    格式化日期对象

    Args:
        date_obj: 日期对象
        fmt: 输出格式

    Returns:
        str: 格式化后的日期字符串
    """
    if isinstance(date_obj, datetime):
        return date_obj.strftime(fmt)
    elif isinstance(date_obj, date):
        return date_obj.strftime(fmt)
    else:
        return str(date_obj)


def get_current_time(timezone: str = "Asia/Shanghai") -> datetime:
    """
    获取当前时间（带时区）

    Args:
        timezone: 时区

    Returns:
        datetime: 当前时间
    """
    tz = pytz.timezone(timezone)
    return datetime.now(tz)


def is_market_open() -> bool:
    """
    判断当前是否在交易时间内（A股）

    Returns:
        bool: 是否在交易时间
    """
    now = get_current_time()

    # 转换为北京时间（确保时区正确）
    if now.tzinfo is None:
        tz = pytz.timezone("Asia/Shanghai")
        now = tz.localize(now)

    current_time = now.time()

    # 周一至周五
    if now.weekday() >= 5:
        return False

    # 上午交易时间：9:30-11:30
    morning_start = datetime.time(datetime(2023, 1, 1, 9, 30))
    morning_end = datetime.time(datetime(2023, 1, 1, 11, 30))

    # 下午交易时间：13:00-15:00
    afternoon_start = datetime.time(datetime(2023, 1, 1, 13, 0))
    afternoon_end = datetime.time(datetime(2023, 1, 1, 15, 0))

    # 检查是否在交易时间段内
    if ((morning_start <= current_time <= morning_end) or
            (afternoon_start <= current_time <= afternoon_end)):
        return True

    return False


def get_time_until_market_close() -> Optional[timedelta]:
    """
    获取距离收盘剩余时间

    Returns:
        timedelta: 剩余时间，如果不在交易日返回None
    """
    if not is_trading_day(datetime.now()):
        return None

    now = get_current_time()
    current_time = now.time()

    # 下午收盘时间
    market_close = datetime.time(datetime(2023, 1, 1, 15, 0))

    # 如果已经收盘或还未开盘
    if current_time > market_close:
        return None

    # 计算时间差
    close_datetime = datetime.combine(now.date(), market_close)
    if now.tzinfo:
        close_datetime = now.tzinfo.localize(close_datetime)

    return close_datetime - now


# 测试函数
def test_date_utils():
    """测试日期工具"""
    print("🧪 测试日期工具...")

    today = date.today()

    # 测试交易日判断
    print(f"今天 {today} 是交易日吗? {is_trading_day(today)}")

    # 测试获取下一个交易日
    next_trading = get_next_trading_day(today)
    print(f"下一个交易日: {next_trading}")

    # 测试获取前一个交易日
    prev_trading = get_previous_trading_day(today)
    print(f"上一个交易日: {prev_trading}")

    # 测试交易日数量
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 31)
    trading_days = get_trading_days_between(start_date, end_date)
    print(f"2023年1月交易日数量: {len(trading_days)}")
    print(f"交易日列表: {trading_days[:5]}...")  # 显示前5个

    # 测试时间判断
    print(f"现在是否在交易时间? {is_market_open()}")

    # 测试距离收盘时间
    time_left = get_time_until_market_close()
    if time_left:
        print(f"距离收盘还有: {time_left}")
    else:
        print("现在不是交易时间")

    print("✅ 日期工具测试完成")


if __name__ == "__main__":
    test_date_utils()