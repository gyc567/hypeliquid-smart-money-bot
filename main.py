#!/usr/bin/env python3
"""
Hypeliquid聪明钱地址监控机器人主程序

这是一个Telegram机器人，用于监控Hypeliquid链上的聪明钱地址动态，
当检测到地址有余额变化或新交易时，会自动向用户发送通知。

作者: Claude Code
版本: 1.0.0
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
import signal
from typing import Optional

from config import Config
from database import DatabaseManager
from telegram_bot import TelegramBot
from scheduler import TaskManager
from error_handler import global_error_handler, send_system_alert, log_and_handle_error

# 配置日志
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class HypeliquidBot:
    """Hypeliquid聪明钱监控机器人主类"""
    
    def __init__(self):
        self.task_manager = None
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # 系统统计
        self.stats = {
            'start_time': None,
            'total_messages': 0,
            'total_notifications': 0,
            'errors_handled': 0
        }
    
    async def initialize(self):
        """初始化机器人"""
        try:
            logger.info("正在初始化Hypeliquid聪明钱监控机器人...")
            
            # 验证环境变量
            Config.validate()
            
            # 创建日志目录
            os.makedirs('logs', exist_ok=True)
            os.makedirs('data', exist_ok=True)
            
            # 初始化任务管理器
            self.task_manager = TaskManager()
            await self.task_manager.initialize(Config.TELEGRAM_BOT_TOKEN)
            
            logger.info("机器人初始化完成")
            
        except Exception as e:
            logger.error(f"机器人初始化失败: {e}")
            await self._handle_fatal_error(e, "initialization")
            raise
    
    async def run(self):
        """运行机器人"""
        try:
            logger.info("启动Hypeliquid聪明钱监控机器人...")
            
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            # 启动任务管理器
            await self.task_manager.run()
            
            # 等待关闭信号
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("收到键盘中断，正在关闭...")
        except Exception as e:
            logger.error(f"机器人运行出错: {e}")
            await self._handle_fatal_error(e, "runtime")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """关闭机器人"""
        try:
            logger.info("正在关闭机器人...")
            
            self.is_running = False
            
            # 停止任务管理器
            if self.task_manager:
                await self.task_manager.cleanup()
            
            # 设置关闭事件
            self.shutdown_event.set()
            
            # 记录最终统计
            self._log_final_stats()
            
            logger.info("机器人已关闭")
            
        except Exception as e:
            logger.error(f"关闭机器人时出错: {e}")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备优雅关闭...")
            asyncio.create_task(self.shutdown())
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Windows系统可能没有SIGUSR1
        if hasattr(signal, 'SIGUSR1'):
            signal.signal(signal.SIGUSR1, signal_handler)
    
    async def _handle_fatal_error(self, error: Exception, error_phase: str):
        """处理致命错误"""
        try:
            logger.critical(f"致命错误 ({error_phase}): {error}")
            
            # 记录错误统计
            self.stats['errors_handled'] += 1
            
            # 发送系统警报
            await send_system_alert(
                'fatal_error',
                f"机器人遇到致命错误 ({error_phase}): {error}",
                'critical'
            )
            
            # 记录详细的错误信息
            error_info = {
                'error_phase': error_phase,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'timestamp': datetime.now(),
                'stats': self.stats
            }
            
            logger.critical(f"错误详情: {error_info}")
            
        except Exception as e:
            logger.error(f"处理致命错误时出错: {e}")
    
    def _log_final_stats(self):
        """记录最终统计信息"""
        try:
            if not self.stats['start_time']:
                return
            
            runtime = datetime.now() - self.stats['start_time']
            
            final_stats = {
                'runtime': str(runtime),
                'total_messages': self.stats['total_messages'],
                'total_notifications': self.stats['total_notifications'],
                'errors_handled': self.stats['errors_handled'],
                'error_handler_stats': global_error_handler.get_error_stats()
            }
            
            logger.info(f"机器人运行统计: {final_stats}")
            
        except Exception as e:
            logger.error(f"记录最终统计时出错: {e}")
    
    def get_status(self) -> dict:
        """获取机器人状态"""
        status = {
            'is_running': self.is_running,
            'start_time': self.stats['start_time'],
            'uptime': None
        }
        
        if self.stats['start_time']:
            status['uptime'] = str(datetime.now() - self.stats['start_time'])
        
        # 添加任务管理器状态
        if self.task_manager:
            status['task_manager'] = self.task_manager.get_status()
        
        return status

async def check_health():
    """健康检查函数"""
    """用于Docker健康检查"""
    try:
        # 检查数据库连接
        db = DatabaseManager(Config.DATABASE_PATH)
        db.get_all_active_addresses()
        
        # 检查配置
        Config.validate()
        
        logger.debug("健康检查通过")
        return True
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return False

async def main():
    """主函数"""
    bot = None
    
    try:
        # 创建机器人实例
        bot = HypeliquidBot()
        
        # 初始化
        await bot.initialize()
        
        # 运行
        await bot.run()
        
    except Exception as e:
        logger.critical(f"程序异常终止: {e}")
        
        # 确保清理资源
        if bot:
            await bot.shutdown()
        
        sys.exit(1)

if __name__ == '__main__':
    # 记录启动信息
    logger.info("=" * 60)
    logger.info("Hypeliquid聪明钱监控机器人启动")
    logger.info(f"启动时间: {datetime.now()}")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"日志级别: {Config.LOG_LEVEL}")
    logger.info("=" * 60)
    
    # 运行主函数
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.critical(f"程序异常退出: {e}")
        sys.exit(1)