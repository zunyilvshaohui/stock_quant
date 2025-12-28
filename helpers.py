#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用辅助函数和工具类
"""

import time
import functools
import json
import pickle
import hashlib
import random
import string
from typing import Any, Callable, Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import numpy as np


def timer(func: Callable) -> Callable:
    """
    计时装饰器

    Args:
        func: 被装饰的函数

    Returns:
        包装后的函数
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed = end_time - start_time

        # 获取logger
        try:
            import logging
            logger = logging.getLogger("quant")
            logger.debug(f"函数 {func.__name__} 执行时间: {elapsed:.4f}秒")
        except:
            print(f"⏱️  函数 {func.__name__} 执行时间: {elapsed:.4f}秒")

        return result

    return wrapper


def retry(max_retries: int = 3, delay: float = 1.0,
          exceptions: tuple = (Exception,)):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries - 1:  # 还有重试机会
                        wait_time = delay * (2 ** attempt)  # 指数退避
                        try:
                            import logging
                            logger = logging.getLogger("quant")
                            logger.warning(
                                f"函数 {func.__name__} 执行失败，"
                                f"{attempt + 1}/{max_retries} 次重试，"
                                f"等待 {wait_time:.1f}秒后重试。错误: {e}"
                            )
                        except:
                            print(f"⚠️  函数 {func.__name__} 执行失败，{attempt + 1}/{max_retries} 次重试")

                        time.sleep(wait_time)
                    else:
                        try:
                            import logging
                            logger = logging.getLogger("quant")
                            logger.error(
                                f"函数 {func.__name__} 重试 {max_retries} 次后仍失败: {e}"
                            )
                        except:
                            print(f"❌ 函数 {func.__name__} 重试 {max_retries} 次后仍失败")

                        raise last_exception

            raise last_exception

        return wrapper

    return decorator


class Singleton(type):
    """
    单例模式元类
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def safe_save(data: Any, filepath: Union[str, Path],
              backup: bool = True) -> bool:
    """
    安全保存数据到文件

    Args:
        data: 要保存的数据
        filepath: 文件路径
        backup: 是否备份原文件

    Returns:
        bool: 是否保存成功
    """
    filepath = Path(filepath)

    try:
        # 创建目录（如果不存在）
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 备份原文件
        if backup and filepath.exists():
            backup_path = filepath.with_suffix(f".backup_{int(time.time())}")
            filepath.rename(backup_path)

        # 根据文件类型选择保存方式
        if filepath.suffix in ['.pkl', '.pickle']:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
        elif filepath.suffix in ['.json', '.jsonl']:
            with open(filepath, 'w', encoding='utf-8') as f:
                if isinstance(data, (pd.DataFrame, pd.Series)):
                    data.to_json(f, orient='records', force_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        elif filepath.suffix in ['.csv']:
            if isinstance(data, (pd.DataFrame, pd.Series)):
                data.to_csv(filepath, index=False, encoding='utf-8-sig')
            else:
                raise ValueError("CSV格式只支持pandas DataFrame或Series")
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(data))

        return True

    except Exception as e:
        print(f"❌ 保存文件失败 {filepath}: {e}")
        return False


def safe_load(filepath: Union[str, Path], default: Any = None) -> Any:
    """
    安全从文件加载数据

    Args:
        filepath: 文件路径
        default: 加载失败时的默认值

    Returns:
        加载的数据或默认值
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return default

    try:
        # 根据文件类型选择加载方式
        if filepath.suffix in ['.pkl', '.pickle']:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        elif filepath.suffix in ['.json', '.jsonl']:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif filepath.suffix in ['.csv']:
            return pd.read_csv(filepath, encoding='utf-8-sig')
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()

    except Exception as e:
        print(f"❌ 加载文件失败 {filepath}: {e}")
        return default


def dataframe_to_dict(df: pd.DataFrame, orient: str = 'records') -> List[Dict]:
    """
    DataFrame转换为字典列表

    Args:
        df: pandas DataFrame
        orient: 转换方向

    Returns:
        字典列表
    """
    if df.empty:
        return []

    # 处理NaN值为None
    df = df.where(pd.notnull(df), None)

    if orient == 'records':
        return df.to_dict('records')
    elif orient == 'list':
        return df.to_dict('list')
    else:
        return df.to_dict()


def dict_to_dataframe(data: List[Dict], **kwargs) -> pd.DataFrame:
    """
    字典列表转换为DataFrame

    Args:
        data: 字典列表
        **kwargs: 传递给pd.DataFrame的额外参数

    Returns:
        pandas DataFrame
    """
    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data, **kwargs)


def generate_id(prefix: str = "", length: int = 8) -> str:
    """
    生成唯一ID

    Args:
        prefix: ID前缀
        length: 随机部分长度

    Returns:
        唯一ID字符串
    """
    timestamp = int(time.time() * 1000)
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return f"{prefix}{timestamp}_{random_str}"


def calculate_md5(filepath: Union[str, Path]) -> str:
    """
    计算文件的MD5哈希值

    Args:
        filepath: 文件路径

    Returns:
        MD5哈希值
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return ""

    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def format_number(value: float, decimals: int = 2,
                  add_commas: bool = True) -> str:
    """
    格式化数字显示

    Args:
        value: 数值
        decimals: 小数位数
        add_commas: 是否添加千分位分隔符

    Returns:
        格式化后的字符串
    """
    if pd.isna(value) or value is None:
        return "N/A"

    # 格式化为指定小数位
    formatted = f"{value:.{decimals}f}"

    # 添加千分位分隔符
    if add_commas and abs(value) >= 1000:
        parts = formatted.split('.')
        parts[0] = "{:,}".format(int(parts[0]))
        formatted = ".".join(parts)

    return formatted


def format_percentage(value: float, decimals: int = 2,
                      add_sign: bool = True) -> str:
    """
    格式化百分比显示

    Args:
        value: 百分比值（如0.05表示5%）
        decimals: 小数位数
        add_sign: 是否添加正负号

    Returns:
        格式化后的字符串
    """
    if pd.isna(value) or value is None:
        return "N/A"

    percentage = value * 100

    sign = ""
    if add_sign and percentage > 0:
        sign = "+"

    return f"{sign}{percentage:.{decimals}f}%"


# 测试函数
def test_helpers():
    """测试辅助函数"""
    print("🧪 测试辅助函数...")

    # 测试计时装饰器
    @timer
    def test_func():
        time.sleep(0.1)
        return "done"

    result = test_func()
    print(f"计时装饰器测试: {result}")

    # 测试格式化函数
    print(f"数字格式化: {format_number(1234567.891, 2)}")
    print(f"百分比格式化: {format_percentage(0.1567, 2)}")

    # 测试DataFrame转换
    data = [
        {"name": "Alice", "age": 25, "score": 85.5},
        {"name": "Bob", "age": 30, "score": 92.0},
    ]
    df = dict_to_dataframe(data)
    print(f"DataFrame转换: {len(df)} 行")

    data_back = dataframe_to_dict(df)
    print(f"字典转换: {len(data_back)} 条记录")

    # 测试ID生成
    print(f"生成ID: {generate_id('TRADE_')}")

    print("✅ 辅助函数测试完成")


if __name__ == "__main__":
    test_helpers()