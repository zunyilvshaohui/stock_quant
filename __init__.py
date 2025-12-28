# config/__init__.py 文件内容
"""
配置模块初始化
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any


class Config:
    """配置管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
        return cls._instance

    def load_config(self, config_path: str = None):
        """加载配置文件"""
        if config_path is None:
            # 默认配置文件路径
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "strategy_config.yaml"

        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        # 根据扩展名选择加载方式
        if config_path.suffix in ['.yaml', '.yml']:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        elif config_path.suffix == '.json':
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")

        return self._config

    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value):
        """设置配置值"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    @property
    def all_config(self):
        """获取全部配置"""
        return self._config


def load_config(config_path: str = None) -> Dict[str, Any]:
    """加载配置的快捷函数"""
    config = Config()
    return config.load_config(config_path)


# 全局配置实例
global_config = Config()