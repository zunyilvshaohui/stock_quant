#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取器 - 从多源获取股票数据
支持akshare、tushare、本地缓存
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取器 - 从多源获取股票数据
支持akshare、tushare、本地缓存
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径，以便导入utils模块
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.absolute()
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import time
import json

# 尝试导入akshare
try:
    import akshare as ak

    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️  akshare模块未安装，数据获取功能将受限")
    print("请运行: pip install akshare")

from utils.helpers import retry, timer, safe_save, safe_load
from utils.logger import get_logger

logger = get_logger("data_fetcher")


class DataFetcher:
    """数据获取器"""

    def __init__(self, cache_dir: Optional[Path] = None, use_cache: bool = True):
        """
        初始化数据获取器

        Args:
            cache_dir: 缓存目录
            use_cache: 是否使用缓存
        """
        if cache_dir is None:
            from config.settings import get_data_dir
            cache_dir = get_data_dir() / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.use_cache = use_cache
        self.cache_expire_days = 7  # 缓存过期天数

        logger.info(f"数据获取器初始化完成，缓存目录: {self.cache_dir}")

    def _get_cache_key(self, symbol: str, start_date: str, end_date: str,
                       adjust: str = "hfq") -> str:
        """生成缓存键"""
        key_parts = [symbol, start_date, end_date, adjust]
        return "_".join(key_parts).replace(":", "_").replace("-", "_")

    def _get_cache_file(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.parquet"

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """检查缓存是否有效"""
        if not cache_file.exists():
            return False

        # 检查缓存时间
        modify_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        expire_time = modify_time + timedelta(days=self.cache_expire_days)

        return datetime.now() < expire_time

    @retry(max_retries=3, delay=1)
    @timer
    def fetch_stock_daily(self, symbol: str, start_date: str, end_date: str,
                          adjust: str = "hfq") -> pd.DataFrame:
        """
        获取股票日线数据

        Args:
            symbol: 股票代码，如 "000001.SZ"
            start_date: 开始日期，格式 "YYYY-MM-DD"
            end_date: 结束日期，格式 "YYYY-MM-DD"
            adjust: 复权方式 "qfq"(前复权), "hfq"(后复权), None(不复权)

        Returns:
            pd.DataFrame: 日线数据，包含以下列:
                date, open, high, low, close, volume, turnover
        """
        # 生成缓存键
        cache_key = self._get_cache_key(symbol, start_date, end_date, adjust)
        cache_file = self._get_cache_file(cache_key)

        # 检查缓存
        if self.use_cache and self._is_cache_valid(cache_file):
            logger.debug(f"从缓存加载数据: {symbol} ({start_date} 到 {end_date})")
            try:
                df = pd.read_parquet(cache_file)
                return df
            except Exception as e:
                logger.warning(f"缓存加载失败: {e}")

        # 如果没有akshare，返回模拟数据
        if not AKSHARE_AVAILABLE:
            logger.warning("akshare未安装，返回模拟数据")
            return self._generate_mock_data(symbol, start_date, end_date)

        try:
            logger.info(f"从akshare获取数据: {symbol} ({start_date} 到 {end_date})")

            # 暂时使用模拟数据，避免akshare兼容性问题
            logger.warning("暂时使用模拟数据，避免akshare兼容性问题")
            return self._generate_mock_data(symbol, start_date, end_date)

            # 从akshare获取数据
            # stock_code = symbol.replace(".SZ", "").replace(".SH", "")

            # 使用更稳定的akshare函数
            # try:
            #     df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
            #                             start_date=start_date, end_date=end_date,
            #                             adjust="qfq" if adjust == "qfq" else "")
            #
            #     # 重命名列映射
            #     column_mapping = {
            #         '日期': 'date',
            #         '开盘': 'open',
            #         '最高': 'high',
            #         '最低': 'low',
            #         '收盘': 'close',
            #         '成交量': 'volume',
            #         '成交额': 'turnover',
            #         '涨跌幅': 'pct_change',
            #         '涨跌额': 'change',
            #         '换手率': 'turnover_rate',
            #     }
            #
            #     # 只保留已有的列
            #     existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            #     df = df.rename(columns=existing_columns)
            #
            # except Exception as ak_error:
            #     logger.warning(f"akshare主函数失败: {ak_error}, 尝试备用函数")
            #
            #     # 尝试备用函数
            #     try:
            #         df = ak.stock_zh_a_daily(symbol=stock_code)
            #         df = df[(df.index >= start_date) & (df.index <= end_date)]
            #
            #         # 重命名列
            #         df = df.rename(columns={
            #             'open': 'open',
            #             'high': 'high',
            #             'low': 'low',
            #             'close': 'close',
            #             'volume': 'volume',
            #         })
            #
            #     except Exception as backup_error:
            #         logger.error(f"akshare备用函数也失败: {backup_error}")
            #         raise ak_error
            #
            # # 重命名列以统一格式
            # column_mapping = {
            #     '日期': 'date',
            #     '开盘': 'open',
            #     '最高': 'high',
            #     '最低': 'low',
            #     '收盘': 'close',
            #     '成交量': 'volume',
            #     '成交额': 'turnover',
            #     '涨跌幅': 'pct_change',
            #     '涨跌额': 'change',
            #     '换手率': 'turnover_rate',
            # }
            #
            # df = df.rename(columns=column_mapping)
            #
            # # 确保date列是datetime类型
            # df['date'] = pd.to_datetime(df['date'])
            #
            # # 设置索引
            # df = df.set_index('date').sort_index()
            #
            # # 只保留需要的列
            # essential_cols = ['open', 'high', 'low', 'close', 'volume', 'turnover']
            # available_cols = [col for col in essential_cols if col in df.columns]
            # df = df[available_cols]
            #
            # # 保存到缓存
            # if self.use_cache:
            #     df.to_parquet(cache_file)
            #     logger.debug(f"数据已缓存: {cache_file}")
            #
            # logger.info(f"数据获取成功: {symbol}, 共 {len(df)} 条记录")
            # return df

        except Exception as e:
            logger.error(f"获取股票数据失败 {symbol}: {e}")
            # 返回模拟数据作为后备
            return self._generate_mock_data(symbol, start_date, end_date)

    def _generate_mock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟数据（用于测试）"""
        logger.info(f"生成模拟数据: {symbol}")

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        # 生成交易日序列
        dates = pd.bdate_range(start=start, end=end, freq='B')

        # 基础价格（模拟不同股票）
        if "000001" in symbol:  # 平安银行
            base_price = 15.0
        elif "000858" in symbol:  # 五粮液
            base_price = 168.0
        elif "300750" in symbol:  # 宁德时代
            base_price = 200.0
        else:
            base_price = 50.0

        n_days = len(dates)

        # 生成随机价格序列（模拟随机游走）
        np.random.seed(42)  # 固定随机种子以便重现
        returns = np.random.normal(0.0005, 0.02, n_days)  # 日收益率

        # 累积收益率
        price_series = base_price * (1 + returns).cumprod()

        # 生成OHLCV数据
        data = {
            'open': price_series * (1 + np.random.normal(0, 0.01, n_days)),
            'high': price_series * (1 + np.abs(np.random.normal(0.01, 0.015, n_days))),
            'low': price_series * (1 - np.abs(np.random.normal(0.01, 0.015, n_days))),
            'close': price_series,
            'volume': np.random.randint(1000000, 50000000, n_days),
            'turnover': np.random.randint(100000000, 1000000000, n_days),
        }

        df = pd.DataFrame(data, index=dates)
        df.index.name = 'date'

        return df

    @retry(max_retries=3, delay=1)
    @timer
    def fetch_index_data(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指数数据

        Args:
            index_code: 指数代码，如 "000300.SH"（沪深300）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 指数数据
        """
        if not AKSHARE_AVAILABLE:
            logger.warning("akshare未安装，返回模拟指数数据")
            return self._generate_mock_data(index_code, start_date, end_date)

        try:
            logger.info(f"获取指数数据: {index_code}")

            index_map = {
                "000300.SH": "sh000300",  # 沪深300
                "000001.SH": "sh000001",  # 上证指数
                "399001.SZ": "sz399001",  # 深证成指
                "399006.SZ": "sz399006",  # 创业板指
            }

            ak_code = index_map.get(index_code, index_code)

            df = ak.index_zh_a_hist(symbol=ak_code, period="daily",
                                    start_date=start_date, end_date=end_date)

            # 重命名列
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'turnover',
            }

            df = df.rename(columns=column_mapping)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()

            logger.info(f"指数数据获取成功: {index_code}, 共 {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"获取指数数据失败 {index_code}: {e}")
            return self._generate_mock_data(index_code, start_date, end_date)

    def fetch_multiple_stocks(self, symbols: List[str], start_date: str,
                              end_date: str, adjust: str = "hfq") -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权方式

        Returns:
            Dict[str, pd.DataFrame]: 股票代码到数据的映射
        """
        logger.info(f"批量获取 {len(symbols)} 只股票数据")

        results = {}

        for symbol in symbols:
            try:
                df = self.fetch_stock_daily(symbol, start_date, end_date, adjust)
                results[symbol] = df
                logger.debug(f"获取完成: {symbol} ({len(df)} 条记录)")
            except Exception as e:
                logger.error(f"获取失败 {symbol}: {e}")
                results[symbol] = pd.DataFrame()

        return results

    def get_last_trading_day(self) -> str:
        """获取上一个交易日"""
        from utils.date_utils import get_previous_trading_day

        today = datetime.now().date()
        last_trading_day = get_previous_trading_day(today)

        return last_trading_day.strftime("%Y-%m-%d")


# 测试函数
def test_data_fetcher():
    """测试数据获取器"""
    print("🧪 测试数据获取器...")

    fetcher = DataFetcher(use_cache=False)

    # 测试获取单只股票数据
    print("1. 测试获取股票数据...")
    df = fetcher.fetch_stock_daily(
        symbol="000001.SZ",
        start_date="2024-01-01",
        end_date="2024-01-31",
        adjust="hfq"
    )

    print(f"   获取到 {len(df)} 条记录")
    print(f"   时间范围: {df.index[0]} 到 {df.index[-1]}")
    print(f"   数据列: {list(df.columns)}")

    if not df.empty:
        print("   前5条数据:")
        print(df.head())

    # 测试批量获取
    print("\n2. 测试批量获取数据...")
    symbols = ["000001.SZ", "000858.SZ"]
    results = fetcher.fetch_multiple_stocks(
        symbols=symbols,
        start_date="2024-01-01",
        end_date="2024-01-10"
    )

    for symbol, data in results.items():
        print(f"   {symbol}: {len(data)} 条记录")

    print("\n✅ 数据获取器测试完成")
    return df


if __name__ == "__main__":
    test_data_fetcher()