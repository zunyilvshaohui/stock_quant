#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票量化交易系统 - 主程序入口
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目路径到系统路径
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# 导入工具模块
try:
    from utils.logger import setup_logger, get_logger
    from utils.notifier import create_notifier_from_config
    print("✅ 工具模块导入成功")
except ImportError as e:
    print(f"❌ 导入工具模块失败: {e}")

# 导入项目模块
try:
    from config import global_config, load_config
    from config.settings import get_project_root, get_log_dir

    print("✅ 配置模块导入成功")
except ImportError as e:
    print(f"❌ 导入配置模块失败: {e}")
    print("请确保项目结构正确")
    sys.exit(1)


def setup_argparse():
    """设置命令行参数"""
    parser = argparse.ArgumentParser(
        description="股票量化交易系统 - 动态CCI策略",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py --mode backtest --strategy cci --symbol 000001.SZ
  python main.py --mode paper --notify dingtalk
  python main.py --mode live --broker mock
        """
    )

    # 运行模式
    parser.add_argument(
        "--mode",
        type=str,
        default="backtest",
        choices=["backtest", "paper", "live"],
        help="运行模式: backtest(回测), paper(模拟), live(实盘)"
    )

    # 策略选择
    parser.add_argument(
        "--strategy",
        type=str,
        default="cci",
        choices=["cci", "macd", "dual_thrust"],
        help="策略类型"
    )

    # 交易标的
    parser.add_argument(
        "--symbol",
        type=str,
        default="000001.SZ",
        help="股票代码，如: 000001.SZ, 600036.SH"
    )

    # 时间范围
    parser.add_argument(
        "--start",
        type=str,
        default="2023-01-01",
        help="开始日期 (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end",
        type=str,
        default="2023-12-31",
        help="结束日期 (YYYY-MM-DD)"
    )

    # 初始资金
    parser.add_argument(
        "--capital",
        type=float,
        default=1000000.0,
        help="初始资金"
    )

    # 通知设置
    parser.add_argument(
        "--notify",
        type=str,
        default="console",
        choices=["none", "console", "dingtalk", "wechat", "all"],
        help="通知方式"
    )

    # 日志级别
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别"
    )

    # 配置文件
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="自定义配置文件路径"
    )

    return parser


def init_project():
    """初始化项目"""
    print("=" * 60)
    print("📊 股票量化交易系统")
    print("=" * 60)

    # 显示项目信息
    print(f"📁 项目路径: {get_project_root()}")
    print(f"📝 日志路径: {get_log_dir()}")
    print(f"🕒 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查重要目录
    required_dirs = ["data", "logs", "results"]
    for dir_name in required_dirs:
        dir_path = get_project_root() / dir_name
        if dir_path.exists():
            print(f"✅ 目录存在: {dir_name}/")
        else:
            print(f"⚠️  目录不存在: {dir_name}/，正在创建...")
            dir_path.mkdir(exist_ok=True)

    print("-" * 60)

    # 初始化日志系统
    try:
        logger = setup_logger(name="quant", log_level="INFO")
        logger.info("✅ 日志系统初始化完成")
        logger.info(f"项目启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"⚠️  日志系统初始化失败: {e}")

    return True


def load_system_config(config_path=None):
    """加载系统配置"""
    try:
        if config_path:
            config = load_config(config_path)
        else:
            # 尝试加载默认配置
            default_configs = [
                "config/strategy_config.yaml",
                "config/strategy_config.yml",
                "config/config.yaml"
            ]

            config_loaded = False
            for config_file in default_configs:
                config_path = get_project_root() / config_file
                if config_path.exists():
                    config = load_config(str(config_path))
                    print(f"✅ 加载配置文件: {config_file}")
                    config_loaded = True
                    break

            if not config_loaded:
                print("⚠️  未找到配置文件，使用默认配置")
                config = {}

        # 显示加载的配置信息
        if config:
            mode = config.get("mode", "backtest")
            print(f"📋 运行模式: {mode}")

            # 显示策略配置
            strategies = config.get("strategies", {})
            for strategy_name, strategy_config in strategies.items():
                if strategy_config.get("enabled", False):
                    print(f"🎯 启用策略: {strategy_name}")

        return config

    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return {}


def run_backtest_mode(args, config):
    """运行回测模式"""
    print("\n🔍 开始回测...")
    print(f"   策略: {args.strategy}")
    print(f"   标的: {args.symbol}")
    print(f"   期间: {args.start} 到 {args.end}")
    print(f"   资金: ¥{args.capital:,.2f}")

    # 这里会调用回测引擎
    print("⏳ 回测引擎正在开发中...")

    # 模拟回测结果
    result = {
        "total_return": 0.152,  # 总收益15.2%
        "annual_return": 0.082,  # 年化8.2%
        "max_drawdown": -0.125,  # 最大回撤12.5%
        "sharpe_ratio": 1.23,  # 夏普比率
        "win_rate": 0.58,  # 胜率58%
        "total_trades": 42  # 总交易次数
    }

    print("\n📊 回测结果:")
    print(f"   总收益: {result['total_return'] * 100:.1f}%")
    print(f"   年化收益: {result['annual_return'] * 100:.1f}%")
    print(f"   最大回撤: {result['max_drawdown'] * 100:.1f}%")
    print(f"   夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"   胜率: {result['win_rate'] * 100:.1f}%")
    print(f"   交易次数: {result['total_trades']}")

    return result


def run_paper_mode(args, config):
    """运行模拟交易模式"""
    print("\n💹 开始模拟交易...")
    print("⏳ 模拟交易系统正在开发中...")

    # 模拟显示
    print("模拟交易功能包括:")
    print("  • 实时数据获取")
    print("  • 策略信号生成")
    print("  • 模拟订单执行")
    print("  • 持仓管理")
    print("  • 风险管理")

    if args.notify != "none":
        print(f"  • 通知服务: {args.notify}")

    return {"status": "running", "mode": "paper"}


def run_live_mode(args, config):
    """运行实盘交易模式"""
    print("\n⚠️  ⚠️  ⚠️  警告: 实盘交易模式")
    print("此模式将连接真实券商API")
    print("请确保您已经:")
    print("  1. 充分测试策略")
    print("  2. 理解所有风险")
    print("  3. 设置好风险控制")

    confirmation = input("\n确认进入实盘模式? (输入 yes 继续): ")
    if confirmation.lower() != "yes":
        print("已取消实盘模式")
        return {"status": "cancelled"}

    print("⏳ 实盘交易系统正在开发中...")
    return {"status": "preparing", "mode": "live"}


def main():
    """主函数"""
    # 初始化项目
    if not init_project():
        return 1

    # 解析命令行参数
    parser = setup_argparse()
    args = parser.parse_args()

    # 加载配置
    config = load_system_config(args.config)

    # 根据模式运行
    if args.mode == "backtest":
        result = run_backtest_mode(args, config)

    elif args.mode == "paper":
        result = run_paper_mode(args, config)

    elif args.mode == "live":
        result = run_live_mode(args, config)

    else:
        print(f"❌ 未知模式: {args.mode}")
        return 1

    # 显示完成信息
    print("\n" + "=" * 60)
    print("✅ 程序执行完成")
    print(f"📊 运行模式: {args.mode}")
    print(f"⏱️  运行时间: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)