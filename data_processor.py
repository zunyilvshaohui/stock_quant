#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理器 - 数据清洗、特征工程、数据转换
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
from typing import List, Dict, Optional, Union, Tuple
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import warnings

warnings.filterwarnings('ignore')

from utils.helpers import timer
from utils.logger import get_logger

logger = get_logger("data_processor")


class DataProcessor:
    """数据处理器"""

    def __init__(self, fill_method: str = "ffill",
                 remove_outliers: bool = True):
        """
        初始化数据处理器

        Args:
            fill_method: 缺失值填充方法 "ffill"(向前填充), "bfill"(向后填充), "interpolate"(插值)
            remove_outliers: 是否移除异常值
        """
        self.fill_method = fill_method
        self.remove_outliers = remove_outliers
        self.scalers = {}  # 存储标准化器

        logger.info(f"数据处理器初始化完成，填充方法: {fill_method}")

    @timer
    def clean_price_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗价格数据

        Args:
            df: 原始价格数据

        Returns:
            pd.DataFrame: 清洗后的数据
        """
        if df.empty:
            logger.warning("输入数据为空")
            return df

        logger.info(f"开始清洗数据，原始形状: {df.shape}")

        # 创建副本避免修改原数据
        df_clean = df.copy()

        # 1. 检查并处理缺失值
        missing_before = df_clean.isnull().sum().sum()
        if missing_before > 0:
            logger.info(f"发现 {missing_before} 个缺失值")

            # 处理缺失值
            if self.fill_method == "ffill":
                df_clean = df_clean.fillna(method='ffill')
            elif self.fill_method == "bfill":
                df_clean = df_clean.fillna(method='bfill')
            elif self.fill_method == "interpolate":
                df_clean = df_clean.interpolate(method='linear')
            else:
                df_clean = df_clean.fillna(method='ffill')

            # 如果还有缺失值（比如开头无法向前填充），用向后填充
            df_clean = df_clean.fillna(method='bfill')

            missing_after = df_clean.isnull().sum().sum()
            logger.info(f"缺失值处理后剩余: {missing_after}")

        # 2. 检查和处理异常值
        if self.remove_outliers and not df_clean.empty:
            df_clean = self._remove_price_outliers(df_clean)

        # 3. 确保价格数据合理性（价格>0，成交量>=0）
        price_cols = ['open', 'high', 'low', 'close']
        volume_cols = ['volume']

        for col in price_cols:
            if col in df_clean.columns:
                # 价格必须大于0
                invalid_mask = df_clean[col] <= 0
                if invalid_mask.any():
                    logger.warning(f"发现 {invalid_mask.sum()} 个非正价格在 {col} 列")
                    # 用前一日价格替换
                    df_clean.loc[invalid_mask, col] = np.nan
                    df_clean[col] = df_clean[col].fillna(method='ffill')

        for col in volume_cols:
            if col in df_clean.columns:
                # 成交量必须>=0
                invalid_mask = df_clean[col] < 0
                if invalid_mask.any():
                    logger.warning(f"发现 {invalid_mask.sum()} 个负成交量在 {col} 列")
                    df_clean.loc[invalid_mask, col] = 0

        # 4. 确保时间序列顺序
        if isinstance(df_clean.index, pd.DatetimeIndex):
            df_clean = df_clean.sort_index()

        logger.info(f"数据清洗完成，最终形状: {df_clean.shape}")
        return df_clean

    def _remove_price_outliers(self, df: pd.DataFrame,
                               method: str = "iqr") -> pd.DataFrame:
        """
        移除价格异常值

        Args:
            df: 价格数据
            method: 异常值检测方法 "iqr"(四分位距), "zscore"(Z分数)

        Returns:
            pd.DataFrame: 移除异常值后的数据
        """
        df_clean = df.copy()
        price_cols = ['open', 'high', 'low', 'close']

        for col in price_cols:
            if col not in df_clean.columns:
                continue

            prices = df_clean[col].dropna()
            if len(prices) < 10:  # 数据太少不处理异常值
                continue

            if method == "iqr":
                # IQR方法
                Q1 = prices.quantile(0.25)
                Q3 = prices.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 3 * IQR
                upper_bound = Q3 + 3 * IQR

                outlier_mask = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)

            elif method == "zscore":
                # Z分数方法
                mean = prices.mean()
                std = prices.std()
                z_scores = (df_clean[col] - mean) / std
                outlier_mask = abs(z_scores) > 3
            else:
                continue

            if outlier_mask.any():
                n_outliers = outlier_mask.sum()
                logger.debug(f"在 {col} 列发现 {n_outliers} 个异常值")

                # 用前一日价格替换异常值
                df_clean.loc[outlier_mask, col] = np.nan
                df_clean[col] = df_clean[col].fillna(method='ffill')

        return df_clean

    @timer
    def add_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加基础特征

        Args:
            df: 价格数据

        Returns:
            pd.DataFrame: 添加特征后的数据
        """
        if df.empty or 'close' not in df.columns:
            return df

        df_featured = df.copy()

        # 1. 价格变化特征
        if 'close' in df_featured.columns:
            # 收益率
            df_featured['returns'] = df_featured['close'].pct_change()

            # 对数收益率（更符合正态分布）
            df_featured['log_returns'] = np.log(df_featured['close'] / df_featured['close'].shift(1))

            # 价格变化
            df_featured['price_change'] = df_featured['close'].diff()

            # 波动率（20日滚动）
            df_featured['volatility_20d'] = df_featured['returns'].rolling(window=20).std()

        # 2. 成交量特征
        if 'volume' in df_featured.columns:
            # 成交量变化率
            df_featured['volume_pct_change'] = df_featured['volume'].pct_change()

            # 成交量均线
            df_featured['volume_ma_5'] = df_featured['volume'].rolling(window=5).mean()
            df_featured['volume_ma_20'] = df_featured['volume'].rolling(window=20).mean()

            # 成交量比率
            df_featured['volume_ratio'] = df_featured['volume'] / df_featured['volume_ma_20']

        # 3. 价格位置特征
        if all(col in df_featured.columns for col in ['high', 'low', 'close']):
            # 当日价格位置（在当日高低点之间的位置）
            df_featured['price_position'] = (df_featured['close'] - df_featured['low']) / \
                                            (df_featured['high'] - df_featured['low'] + 1e-8)

            # 振幅
            df_featured['amplitude'] = (df_featured['high'] - df_featured['low']) / \
                                       df_featured['close'].shift(1)

        # 4. 时间特征
        if isinstance(df_featured.index, pd.DatetimeIndex):
            # 星期几（0=周一, 6=周日）
            df_featured['day_of_week'] = df_featured.index.dayofweek

            # 月份
            df_featured['month'] = df_featured.index.month

            # 是否为月初/月末
            df_featured['is_month_start'] = df_featured.index.is_month_start.astype(int)
            df_featured['is_month_end'] = df_featured.index.is_month_end.astype(int)

        # 5. 趋势特征
        if 'close' in df_featured.columns:
            # 简单移动平均
            df_featured['sma_5'] = df_featured['close'].rolling(window=5).mean()
            df_featured['sma_20'] = df_featured['close'].rolling(window=20).mean()
            df_featured['sma_60'] = df_featured['close'].rolling(window=60).mean()

            # 价格与均线关系
            df_featured['price_vs_sma20'] = df_featured['close'] / df_featured['sma_20'] - 1

        logger.info(f"添加了 {len(df_featured.columns) - len(df.columns)} 个特征")
        return df_featured

    @timer
    def normalize_features(self, df: pd.DataFrame,
                           feature_cols: List[str] = None,
                           method: str = "standard",
                           fit: bool = True) -> pd.DataFrame:
        """
        特征标准化/归一化

        Args:
            df: 包含特征的数据
            feature_cols: 需要标准化的特征列，None表示自动选择
            method: 标准化方法 "standard"(Z-score), "minmax"(Min-Max)
            fit: 是否拟合新的标准化器

        Returns:
            pd.DataFrame: 标准化后的数据
        """
        if df.empty:
            return df

        df_norm = df.copy()

        # 确定需要标准化的特征列
        if feature_cols is None:
            # 自动选择数值型特征（排除价格和成交量基础列）
            exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'turnover']
            numeric_cols = df_norm.select_dtypes(include=[np.number]).columns
            feature_cols = [col for col in numeric_cols if col not in exclude_cols]

        if not feature_cols:
            logger.warning("没有找到需要标准化的特征列")
            return df_norm

        logger.info(f"标准化 {len(feature_cols)} 个特征，方法: {method}")

        # 创建或获取标准化器
        scaler_key = "_".join(sorted(feature_cols))

        if fit or scaler_key not in self.scalers:
            if method == "standard":
                self.scalers[scaler_key] = StandardScaler()
            elif method == "minmax":
                self.scalers[scaler_key] = MinMaxScaler()
            else:
                self.scalers[scaler_key] = StandardScaler()

            # 拟合标准化器
            self.scalers[scaler_key].fit(df_norm[feature_cols].fillna(0))

        # 应用标准化
        scaled_data = self.scalers[scaler_key].transform(df_norm[feature_cols].fillna(0))

        # 创建新列名
        scaled_cols = [f"{col}_scaled" for col in feature_cols]
        df_scaled = pd.DataFrame(scaled_data, index=df_norm.index, columns=scaled_cols)

        # 合并到原数据
        df_norm = pd.concat([df_norm, df_scaled], axis=1)

        return df_norm

    def prepare_train_test_split(self, df: pd.DataFrame,
                                 test_size: float = 0.2,
                                 date_split: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        准备训练集和测试集

        Args:
            df: 完整数据
            test_size: 测试集比例（0-1之间）
            date_split: 按日期分割，如 "2023-01-01"

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: 训练集，测试集
        """
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        if date_split:
            # 按日期分割
            split_date = pd.to_datetime(date_split)
            train_data = df[df.index < split_date]
            test_data = df[df.index >= split_date]
        else:
            # 按比例分割
            split_idx = int(len(df) * (1 - test_size))
            train_data = df.iloc[:split_idx]
            test_data = df.iloc[split_idx:]

        logger.info(f"数据分割完成: 训练集 {len(train_data)} 条, 测试集 {len(test_data)} 条")

        return train_data, test_data

    def create_lagged_features(self, df: pd.DataFrame,
                               feature_cols: List[str],
                               lags: List[int] = None) -> pd.DataFrame:
        """
        创建滞后特征

        Args:
            df: 原始数据
            feature_cols: 需要创建滞后特征的列
            lags: 滞后阶数，如 [1, 2, 3, 5, 10]

        Returns:
            pd.DataFrame: 添加滞后特征后的数据
        """
        if lags is None:
            lags = [1, 2, 3, 5, 10, 20]

        df_lagged = df.copy()

        for col in feature_cols:
            if col not in df_lagged.columns:
                continue

            for lag in lags:
                lag_col_name = f"{col}_lag_{lag}"
                df_lagged[lag_col_name] = df_lagged[col].shift(lag)

        logger.info(f"创建了 {len(feature_cols) * len(lags)} 个滞后特征")
        return df_lagged

    def calculate_correlation_matrix(self, df: pd.DataFrame,
                                     method: str = "pearson") -> pd.DataFrame:
        """
        计算特征相关性矩阵

        Args:
            df: 特征数据
            method: 相关性计算方法 "pearson", "spearman", "kendall"

        Returns:
            pd.DataFrame: 相关性矩阵
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) < 2:
            return pd.DataFrame()

        corr_matrix = df[numeric_cols].corr(method=method)
        return corr_matrix


# 测试函数
def test_data_processor():
    """测试数据处理器"""
    print("🧪 测试数据处理器...")

    # 创建测试数据
    dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq='B')
    np.random.seed(42)

    test_data = pd.DataFrame({
        'open': np.random.normal(100, 5, len(dates)),
        'high': np.random.normal(105, 5, len(dates)),
        'low': np.random.normal(95, 5, len(dates)),
        'close': np.random.normal(100, 5, len(dates)),
        'volume': np.random.randint(1000000, 50000000, len(dates)),
    }, index=dates)

    # 故意添加一些缺失值和异常值
    test_data.loc[dates[5], 'close'] = np.nan
    test_data.loc[dates[10], 'close'] = 200  # 异常值

    print(f"原始数据形状: {test_data.shape}")
    print(f"原始数据列: {list(test_data.columns)}")

    # 创建数据处理器
    processor = DataProcessor(fill_method="ffill", remove_outliers=True)

    # 测试数据清洗
    print("\n1. 测试数据清洗...")
    cleaned_data = processor.clean_price_data(test_data)
    print(f"清洗后形状: {cleaned_data.shape}")
    print(f"缺失值数量: {cleaned_data.isnull().sum().sum()}")

    # 测试特征工程
    print("\n2. 测试特征工程...")
    featured_data = processor.add_basic_features(cleaned_data)
    print(f"添加特征后形状: {featured_data.shape}")
    print(f"特征数量: {len(featured_data.columns)}")
    print(f"新特征示例: {list(featured_data.columns)[-5:]}")

    # 测试数据标准化
    print("\n3. 测试特征标准化...")
    normalized_data = processor.normalize_features(featured_data, method="standard")
    print(f"标准化后形状: {normalized_data.shape}")

    # 测试数据分割
    print("\n4. 测试数据分割...")
    train_data, test_data = processor.prepare_train_test_split(normalized_data, test_size=0.3)
    print(f"训练集: {len(train_data)} 条记录")
    print(f"测试集: {len(test_data)} 条记录")

    # 测试相关性计算
    print("\n5. 测试相关性计算...")
    corr_matrix = processor.calculate_correlation_matrix(featured_data)
    if not corr_matrix.empty:
        print(f"相关性矩阵形状: {corr_matrix.shape}")
        print("与收盘价相关性最高的5个特征:")
        if 'close' in corr_matrix.columns:
            close_corr = corr_matrix['close'].abs().sort_values(ascending=False)
            print(close_corr.head(5))

    print("\n✅ 数据处理器测试完成")
    return featured_data


if __name__ == "__main__":
    test_data_processor()