import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot配置
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Hyperliquid API配置
    HYPERLIQUID_API_BASE = "https://api.hyperliquid.xyz"
    HYPERLIQUID_EVM_RPC = os.getenv('HYPERLIQUID_RPC_URL', 'https://rpc.hyperliquid.xyz/evm')
    
    # 数据库配置
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'smart_money_monitor.db')
    
    # 监控配置
    DEFAULT_SCAN_INTERVAL = int(os.getenv('DEFAULT_SCAN_INTERVAL', '60'))  # 默认60秒
    MAX_ADDRESSES_PER_USER = int(os.getenv('MAX_ADDRESSES_PER_USER', '20'))
    
    # 性能配置
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', '2'))  # 每秒最大请求数
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))  # 请求超时时间
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # 反垃圾配置
    MAX_USER_MESSAGES_PER_MINUTE = int(os.getenv('MAX_USER_MESSAGES_PER_MINUTE', '10'))

    @staticmethod
    def validate():
        """验证必要的配置项"""
        if not Config.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN环境变量未设置")
        return True