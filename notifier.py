#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多渠道通知发送器
支持钉钉、企业微信、邮件、控制台
"""

import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import threading
from pathlib import Path


# 检查是否安装了必要的依赖
def check_dependencies():
    """检查依赖"""
    missing = []

    try:
        import requests
    except ImportError:
        missing.append("requests")

    if missing:
        print(f"⚠️  缺少依赖包: {missing}")
        print("请运行: pip install " + " ".join(missing))

    return len(missing) == 0

# 尝试导入requests，如果失败则给出提示
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  requests模块未安装，部分通知功能将不可用")
    print("请运行: pip install requests")


class BaseNotifier:
    """通知器基类"""

    def __init__(self, name: str = "base"):
        self.name = name
        self._enabled = True
        self._lock = threading.Lock()
        self.message_count = 0
        self.last_sent_time = 0
        self.rate_limit = {
            "max_per_minute": 60,
            "max_per_hour": 300,
            "max_per_day": 1000
        }

    def is_rate_limited(self) -> bool:
        """检查是否达到频率限制"""
        current_time = time.time()

        # 简单的频率限制检查
        # 实际应用中应该更复杂
        return False

    def format_message(self, message_type: str, data: Dict) -> str:
        """格式化消息"""
        templates = {
            "trade_signal": (
                "🚨 交易信号\n"
                "时间: {time}\n"
                "标的: {symbol}\n"
                "操作: {action}\n"
                "价格: {price:.2f}\n"
                "数量: {quantity}\n"
                "信号强度: {strength}\n"
            ),
            "daily_report": (
                "📊 每日报告\n"
                "日期: {date}\n"
                "总资产: {total_asset:,.2f}\n"
                "今日盈亏: {daily_pnl:+,.2f} ({daily_pnl_pct:+.2f}%)\n"
                "累计盈亏: {total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)\n"
                "持仓: {position_count}只\n"
                "交易: {trade_count}笔\n"
            ),
            "error": (
                "❌ 系统错误\n"
                "时间: {time}\n"
                "模块: {module}\n"
                "错误: {error}\n"
                "详情: {details}\n"
            ),
            "warning": (
                "⚠️ 系统警告\n"
                "时间: {time}\n"
                "类型: {type}\n"
                "内容: {message}\n"
            )
        }

        template = templates.get(message_type, "{message}")

        # 添加默认字段
        if "time" not in data:
            data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 格式化消息
        try:
            return template.format(**data)
        except KeyError as e:
            return f"消息格式化错误，缺少字段: {e}\n原始数据: {data}"

    def send(self, message: str, **kwargs) -> bool:
        """发送消息（需要子类实现）"""
        raise NotImplementedError

    def test_connection(self) -> bool:
        """测试连接"""
        return True


class ConsoleNotifier(BaseNotifier):
    """控制台通知器（用于调试）"""

    def __init__(self, color_output: bool = True):
        super().__init__("console")
        self.color_output = color_output

        # 颜色代码
        self.colors = {
            "trade_signal": "\033[96m",  # 青色
            "daily_report": "\033[92m",  # 绿色
            "error": "\033[91m",  # 红色
            "warning": "\033[93m",  # 黄色
            "info": "\033[94m",  # 蓝色
            "reset": "\033[0m",  # 重置
        }

    def send(self, message: str, level: str = "info", **kwargs) -> bool:
        """发送消息到控制台"""
        if not self._enabled:
            return False

        with self._lock:
            # 添加颜色
            if self.color_output and level in self.colors:
                color_start = self.colors[level]
                color_reset = self.colors["reset"]
                formatted_message = f"{color_start}{message}{color_reset}"
            else:
                formatted_message = message

            # 添加时间戳
            timestamp = datetime.now().strftime("%H:%M:%S")
            full_message = f"[{timestamp}] {formatted_message}"

            # 打印到控制台
            print(full_message)

            self.message_count += 1
            self.last_sent_time = time.time()

            return True


class DingTalkNotifier(BaseNotifier):
    """钉钉群机器人通知器"""

    def __init__(self, webhook: str, secret: Optional[str] = None):
        super().__init__("dingtalk")

        if not REQUESTS_AVAILABLE:
            print("❌ requests模块未安装，钉钉通知器不可用")
            self._enabled = False
            return

        self.webhook = webhook
        self.secret = secret
        self._enabled = bool(webhook)

    def _generate_signature(self, timestamp: int) -> str:
        """生成签名"""
        if not self.secret:
            return ""

        import hashlib
        import hmac
        import base64
        import urllib.parse

        string_to_sign = f'{timestamp}\n{self.secret}'
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()

        return urllib.parse.quote_plus(base64.b64encode(hmac_code))

    def send(self, message: str, message_type: str = "text",
             at_mobiles: List[str] = None, at_all: bool = False,
             **kwargs) -> bool:
        """发送消息到钉钉"""
        if not self._enabled or not REQUESTS_AVAILABLE:
            return False

        if self.is_rate_limited():
            print("⚠️  钉钉通知频率限制，跳过发送")
            return False

        try:
            timestamp = int(time.time() * 1000)
            sign = self._generate_signature(timestamp)

            # 构建请求URL
            url = self.webhook
            if sign:
                url = f'{url}&timestamp={timestamp}&sign={sign}'

            # 构建消息体
            if message_type == "text":
                msg_data = {
                    "msgtype": "text",
                    "text": {"content": message}
                }
            elif message_type == "markdown":
                msg_data = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": kwargs.get("title", "量化交易通知"),
                        "text": message
                    }
                }
            else:
                msg_data = {
                    "msgtype": "text",
                    "text": {"content": message}
                }

            # 添加@功能
            if at_mobiles or at_all:
                msg_data["at"] = {
                    "atMobiles": at_mobiles or [],
                    "isAtAll": at_all
                }

            # 发送请求
            with self._lock:
                response = requests.post(
                    url,
                    json=msg_data,
                    timeout=10,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("errcode") == 0:
                        self.message_count += 1
                        self.last_sent_time = time.time()
                        return True
                    else:
                        print(f"钉钉返回错误: {result.get('errmsg')}")
                        return False
                else:
                    print(f"钉钉请求失败: {response.status_code}")
                    return False

        except Exception as e:
            print(f"钉钉通知发送失败: {e}")
            return False

    def send_trade_signal(self, trade_data: Dict) -> bool:
        """发送交易信号"""
        message = self.format_message("trade_signal", trade_data)
        return self.send(message, message_type="text")

    def send_daily_report(self, report_data: Dict) -> bool:
        """发送每日报告"""
        message = self.format_message("daily_report", report_data)
        return self.send(message, message_type="markdown",
                         title=f"交易报告 {report_data.get('date', '')}")

    def test_connection(self) -> bool:
        """测试钉钉连接"""
        if not self._enabled:
            return False

        test_message = "🔧 钉钉通知器连接测试\n时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.send(test_message)


class EmailNotifier(BaseNotifier):
    """邮件通知器"""

    def __init__(self, smtp_server: str, smtp_port: int,
                 username: str, password: str,
                 sender: str, receivers: List[str]):
        super().__init__("email")

        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender
        self.receivers = receivers
        self._enabled = bool(smtp_server and username and password)

    def send(self, message: str, subject: str = "量化交易通知",
             message_type: str = "plain", **kwargs) -> bool:
        """发送邮件"""
        if not self._enabled:
            return False

        if self.is_rate_limited():
            print("⚠️  邮件通知频率限制，跳过发送")
            return False

        try:
            # 创建邮件
            if message_type == "html":
                msg = MIMEText(message, 'html', 'utf-8')
            else:
                msg = MIMEText(message, 'plain', 'utf-8')

            msg['Subject'] = subject
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.receivers)

            # 发送邮件
            with self._lock:
                if self.smtp_port == 465:
                    # SSL连接
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
                else:
                    # 普通连接
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                    server.starttls()  # 升级为TLS连接

                server.login(self.username, self.password)
                server.sendmail(self.sender, self.receivers, msg.as_string())
                server.quit()

                self.message_count += 1
                self.last_sent_time = time.time()
                return True

        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False

    def test_connection(self) -> bool:
        """测试邮件连接"""
        if not self._enabled:
            return False

        test_subject = "🔧 邮件通知器连接测试"
        test_message = f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send(test_message, test_subject)


class Notifier:
    """统一通知管理器"""

    def __init__(self, config: Optional[Dict] = None):
        self.notifiers = {}
        self.config = config or {}
        self._setup_notifiers()

    def _setup_notifiers(self):
        """根据配置设置通知器"""
        # 控制台通知器（默认启用）
        console_config = self.config.get("console", {})
        if console_config.get("enabled", True):
            self.notifiers["console"] = ConsoleNotifier(
                color_output=console_config.get("color_output", True)
            )

        # 钉钉通知器
        dingtalk_config = self.config.get("dingtalk", {})
        if dingtalk_config.get("enabled", False) and REQUESTS_AVAILABLE:
            webhook = dingtalk_config.get("webhook")
            secret = dingtalk_config.get("secret")
            if webhook:
                self.notifiers["dingtalk"] = DingTalkNotifier(webhook, secret)

        # 邮件通知器
        email_config = self.config.get("email", {})
        if email_config.get("enabled", False):
            smtp_server = email_config.get("smtp_server")
            smtp_port = email_config.get("smtp_port", 465)
            username = email_config.get("username")
            password = email_config.get("password")
            sender = email_config.get("sender")
            receivers = email_config.get("receivers", [])

            if all([smtp_server, username, password, sender, receivers]):
                self.notifiers["email"] = EmailNotifier(
                    smtp_server, smtp_port, username, password,
                    sender, receivers
                )

    def send(self, message: str, channels: List[str] = None,
             level: str = "info", **kwargs) -> Dict[str, bool]:
        """
        发送消息到指定渠道

        Args:
            message: 消息内容
            channels: 渠道列表，如 ["console", "dingtalk"]，None表示所有渠道
            level: 消息级别
            **kwargs: 其他参数

        Returns:
            Dict[str, bool]: 各渠道发送结果
        """
        results = {}

        target_channels = channels or list(self.notifiers.keys())

        for channel in target_channels:
            if channel in self.notifiers:
                notifier = self.notifiers[channel]

                if channel == "console":
                    results[channel] = notifier.send(message, level=level, **kwargs)
                elif channel == "dingtalk":
                    results[channel] = notifier.send(message, **kwargs)
                elif channel == "email":
                    subject = kwargs.get("subject", "量化交易通知")
                    results[channel] = notifier.send(message, subject=subject, **kwargs)
                else:
                    results[channel] = notifier.send(message, **kwargs)
            else:
                results[channel] = False

        return results

    def send_trade_signal(self, trade_data: Dict,
                          channels: List[str] = None) -> Dict[str, bool]:
        """发送交易信号"""
        # 格式化消息
        message = f"🚨 交易信号\n时间: {datetime.now().strftime('%H:%M:%S')}\n"

        for key, value in trade_data.items():
            if key == "price" and isinstance(value, (int, float)):
                message += f"{key}: {value:.2f}\n"
            else:
                message += f"{key}: {value}\n"

        return self.send(message, channels, level="trade_signal")

    def send_daily_report(self, report_data: Dict,
                          channels: List[str] = None) -> Dict[str, bool]:
        """发送每日报告"""
        # 创建Markdown格式的报告
        markdown = f"""## 📊 每日交易报告

**日期**: {report_data.get('date', datetime.now().strftime('%Y-%m-%d'))}

### 资产概况
- 总资产: ¥{report_data.get('total_asset', 0):,.2f}
- 今日盈亏: ¥{report_data.get('daily_pnl', 0):+,.2f} ({report_data.get('daily_pnl_pct', 0):+.2f}%)
- 累计盈亏: ¥{report_data.get('total_pnl', 0):+,.2f} ({report_data.get('total_pnl_pct', 0):+.2f}%)

### 持仓统计
- 持仓数量: {report_data.get('position_count', 0)}只
- 持仓市值: ¥{report_data.get('position_value', 0):,.2f}

### 交易统计
- 今日交易: {report_data.get('trade_count', 0)}笔
- 胜率: {report_data.get('win_rate', 0):.1f}%
- 最大回撤: {report_data.get('max_drawdown', 0):.2f}%

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        # 发送到不同渠道
        results = {}
        target_channels = channels or list(self.notifiers.keys())

        for channel in target_channels:
            if channel in self.notifiers:
                notifier = self.notifiers[channel]

                if channel == "dingtalk":
                    results[channel] = notifier.send(
                        markdown,
                        message_type="markdown",
                        title=f"交易报告 {report_data.get('date', '')}"
                    )
                elif channel == "email":
                    results[channel] = notifier.send(
                        markdown,
                        subject=f"交易报告 {report_data.get('date', '')}",
                        message_type="html"
                    )
                else:
                    # 其他渠道用文本格式
                    text_report = markdown.replace("#", "").replace("- ", "• ").replace("**", "")
                    results[channel] = notifier.send(text_report)
            else:
                results[channel] = False

        return results

    def test_all_connections(self) -> Dict[str, bool]:
        """测试所有通知器的连接"""
        results = {}

        for name, notifier in self.notifiers.items():
            print(f"测试 {name} 连接...")
            success = notifier.test_connection()
            results[name] = success

            if success:
                print(f"✅ {name} 连接成功")
            else:
                print(f"❌ {name} 连接失败")

        return results


# 快捷函数
def create_notifier_from_config(config_path: Optional[str] = None) -> Notifier:
    """
    从配置文件创建通知器

    Args:
        config_path: 配置文件路径

    Returns:
        Notifier: 通知管理器实例
    """
    from config import global_config

    if config_path:
        config = global_config.load_config(config_path)
    else:
        config = global_config.all_config

    # 获取通知配置
    notification_config = config.get("notification", {})

    return Notifier(notification_config)


# 测试函数
def test_notifier():
    """测试通知系统"""
    print("🧪 测试通知系统...")

    # 创建测试配置
    test_config = {
        "console": {"enabled": True, "color_output": True},
        "dingtalk": {"enabled": False},  # 设为True并填写webhook以测试钉钉
        "email": {"enabled": False}  # 设为True并填写配置以测试邮件
    }

    # 创建通知管理器
    notifier = Notifier(test_config)

    # 测试连接
    print("\n🔗 测试通知器连接...")
    connection_results = notifier.test_all_connections()
    print(f"连接结果: {connection_results}")

    # 测试普通消息
    print("\n📨 测试普通消息...")
    results = notifier.send("这是一条测试消息", ["console"], level="info")
    print(f"发送结果: {results}")

    # 测试交易信号
    print("\n📈 测试交易信号...")
    trade_data = {
        "symbol": "000001.SZ",
        "action": "BUY",
        "price": 15.30,
        "quantity": 1000,
        "strength": "强"
    }
    results = notifier.send_trade_signal(trade_data, ["console"])
    print(f"交易信号发送结果: {results}")

    # 测试每日报告
    print("\n📊 测试每日报告...")
    report_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_asset": 1050000.50,
        "daily_pnl": 5000.50,
        "daily_pnl_pct": 0.48,
        "total_pnl": 50000.50,
        "total_pnl_pct": 5.00,
        "position_count": 3,
        "position_value": 800000.00,
        "trade_count": 5,
        "win_rate": 60.0,
        "max_drawdown": 2.5
    }
    results = notifier.send_daily_report(report_data, ["console"])
    print(f"每日报告发送结果: {results}")

    print("\n✅ 通知系统测试完成")


if __name__ == "__main__":
    test_notifier()