import asyncio
import logging
import signal
import sys
from typing import Optional
import time
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import Config
from database import DatabaseManager
from telegram_bot import TelegramBot
from monitor import AddressMonitor, NotificationProcessor

logger = logging.getLogger(__name__)

class TaskScheduler:
    """任务调度器 - 负责协调所有定时任务"""
    
    def __init__(self, database: DatabaseManager, telegram_bot: TelegramBot):
        self.db = database
        self.telegram_bot = telegram_bot
        self.scheduler = None
        self.address_monitor = None
        self.notification_processor = None
        
        # 运行状态
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # 统计信息
        self.stats = {
            'scheduler_start_time': None,
            'total_tasks_executed': 0,
            'failed_tasks': 0
        }
    
    async def initialize(self):
        """初始化调度器"""
        try:
            # 创建调度器
            self.scheduler = AsyncIOScheduler(
                job_defaults={
                    'coalesce': True,  # 合并错过的任务
                    'max_instances': 1,  # 同一任务同时只能有一个实例运行
                    'misfire_grace_time': 300  # 任务错过执行时间的宽限期（5分钟）
                }
            )
            
            # 创建监控器和通知处理器
            self.address_monitor = AddressMonitor(self.db)
            
            logger.info("任务调度器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化调度器失败: {e}")
            raise
    
    async def start(self):
        """启动调度器"""
        try:
            if not self.scheduler:
                await self.initialize()
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            # 添加定时任务
            self._setup_scheduled_tasks()
            
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            self.stats['scheduler_start_time'] = datetime.now()
            
            logger.info("任务调度器启动成功")
            
            # 启动监控器和通知处理器
            await self._start_background_services()
            
            # 等待关闭信号
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """关闭调度器"""
        try:
            logger.info("正在关闭任务调度器...")
            
            self.is_running = False
            
            # 停止后台服务
            await self._stop_background_services()
            
            # 停止调度器
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("调度器已停止")
            
            # 设置关闭事件
            self.shutdown_event.set()
            
            logger.info("任务调度器关闭完成")
            
        except Exception as e:
            logger.error(f"关闭调度器失败: {e}")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备关闭...")
            asyncio.create_task(self.shutdown())
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_scheduled_tasks(self):
        """设置定时任务"""
        try:
            # 1. 地址扫描任务 - 每30秒执行一次
            self.scheduler.add_job(
                func=self._scan_addresses_task,
                trigger=IntervalTrigger(seconds=30),
                id='scan_addresses',
                name='扫描监控地址',
                replace_existing=True
            )
            
            # 2. 通知处理任务 - 每10秒执行一次
            self.scheduler.add_job(
                func=self._process_notifications_task,
                trigger=IntervalTrigger(seconds=10),
                id='process_notifications',
                name='处理待发送通知',
                replace_existing=True
            )
            
            # 3. 数据清理任务 - 每天凌晨2点执行
            self.scheduler.add_job(
                func=self._cleanup_data_task,
                trigger=CronTrigger(hour=2, minute=0),
                id='cleanup_data',
                name='清理旧数据',
                replace_existing=True
            )
            
            # 4. 健康检查任务 - 每5分钟执行一次
            self.scheduler.add_job(
                func=self._health_check_task,
                trigger=IntervalTrigger(minutes=5),
                id='health_check',
                name='系统健康检查',
                replace_existing=True
            )
            
            # 5. 统计报告任务 - 每小时执行一次
            self.scheduler.add_job(
                func=self._generate_stats_report_task,
                trigger=IntervalTrigger(hours=1),
                id='generate_stats',
                name='生成统计报告',
                replace_existing=True
            )
            
            logger.info(f"已添加 {len(self.scheduler.get_jobs())} 个定时任务")
            
        except Exception as e:
            logger.error(f"设置定时任务失败: {e}")
            raise
    
    async def _start_background_services(self):
        """启动后台服务"""
        try:
            # 启动地址监控器
            if self.address_monitor:
                asyncio.create_task(self.address_monitor.start_monitoring())
                logger.info("地址监控器已启动")
            
            # 启动通知处理器（需要Telegram Bot应用）
            if self.telegram_bot.application and self.notification_processor:
                asyncio.create_task(self.notification_processor.start_processing())
                logger.info("通知处理器已启动")
            
        except Exception as e:
            logger.error(f"启动后台服务失败: {e}")
            raise
    
    async def _stop_background_services(self):
        """停止后台服务"""
        try:
            # 停止地址监控器
            if self.address_monitor:
                await self.address_monitor.stop_monitoring()
                logger.info("地址监控器已停止")
            
            # 停止通知处理器
            if self.notification_processor:
                await self.notification_processor.stop_processing()
                logger.info("通知处理器已停止")
                
        except Exception as e:
            logger.error(f"停止后台服务失败: {e}")
    
    async def _scan_addresses_task(self):
        """地址扫描任务"""
        try:
            logger.debug("执行地址扫描任务")
            start_time = time.time()
            
            # 获取所有活跃的监控地址
            active_addresses = self.db.get_all_active_addresses()
            
            if not active_addresses:
                logger.debug("没有活跃的监控地址")
                return
            
            logger.info(f"开始扫描 {len(active_addresses)} 个地址")
            
            # 执行扫描（这里简化处理，实际应该调用监控器的扫描逻辑）
            # 由于监控器已经在后台运行，这里可以做一些额外的统计或检查
            
            scan_duration = time.time() - start_time
            logger.info(f"地址扫描任务完成，耗时: {scan_duration:.2f}秒")
            
            self.stats['total_tasks_executed'] += 1
            
        except Exception as e:
            logger.error(f"地址扫描任务失败: {e}")
            self.stats['failed_tasks'] += 1
    
    async def _process_notifications_task(self):
        """处理待发送通知任务"""
        try:
            logger.debug("执行通知处理任务")
            
            # 获取待发送的通知
            pending_notifications = self.db.get_pending_notifications(limit=100)
            
            if not pending_notifications:
                return
            
            logger.info(f"处理 {len(pending_notifications)} 个待发送通知")
            
            # 发送通知（需要Telegram Bot）
            for notification in pending_notifications:
                try:
                    await self._send_notification(notification)
                    
                    # 标记为已发送
                    self.db.mark_notification_sent(notification['id'])
                    
                except Exception as e:
                    logger.error(f"发送通知失败 {notification['id']}: {e}")
                    # 不标记为已发送，下次会重试
            
            logger.info(f"通知处理任务完成，处理了 {len(pending_notifications)} 个通知")
            
        except Exception as e:
            logger.error(f"通知处理任务失败: {e}")
            self.stats['failed_tasks'] += 1
    
    async def _send_notification(self, notification: Dict):
        """发送通知"""
        try:
            if not self.telegram_bot.application:
                logger.warning("Telegram Bot 未初始化，无法发送通知")
                return
            
            user_id = notification['user_id']
            message = notification['message']
            
            # 通过 Telegram Bot 发送消息
            await self.telegram_bot.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.debug(f"通知发送成功: 用户 {user_id}")
            
        except Exception as e:
            logger.error(f"发送通知消息失败: {e}")
            raise  # 重新抛出异常，让上层处理
    
    async def _cleanup_data_task(self):
        """数据清理任务"""
        try:
            logger.info("执行数据清理任务")
            
            # 清理30天前的旧数据
            days_to_keep = 30
            success = self.db.cleanup_old_data(days_to_keep)
            
            if success:
                logger.info(f"数据清理完成，保留最近 {days_to_keep} 天的数据")
            else:
                logger.error("数据清理失败")
            
        except Exception as e:
            logger.error(f"数据清理任务失败: {e}")
            self.stats['failed_tasks'] += 1
    
    async def _health_check_task(self):
        """健康检查任务"""
        try:
            logger.debug("执行健康检查任务")
            
            # 检查数据库连接
            try:
                active_addresses = self.db.get_all_active_addresses()
                db_status = "正常"
            except Exception as e:
                db_status = f"异常: {e}"
                logger.error(f"数据库连接异常: {e}")
            
            # 检查地址监控器状态
            monitor_status = "运行中" if self.address_monitor and self.address_monitor.is_running else "未运行"
            
            # 获取监控统计
            if self.address_monitor:
                monitor_stats = self.address_monitor.get_stats()
            else:
                monitor_stats = {}
            
            # 记录健康状态
            logger.info(f"健康检查 - 数据库: {db_status}, 监控器: {monitor_status}, "
                       f"监控地址: {len(active_addresses) if db_status == '正常' else '未知'}")
            
            # 如果有严重问题，可以在这里发送警报
            if db_status != "正常":
                logger.error("数据库连接异常，需要人工干预")
            
            if monitor_status == "未运行":
                logger.error("地址监控器未运行，尝试重启")
                if self.address_monitor:
                    asyncio.create_task(self.address_monitor.start_monitoring())
            
        except Exception as e:
            logger.error(f"健康检查任务失败: {e}")
            self.stats['failed_tasks'] += 1
    
    async def _generate_stats_report_task(self):
        """生成统计报告任务"""
        try:
            logger.info("生成统计报告")
            
            # 收集统计信息
            stats_data = {
                'scheduler_stats': self.stats,
                'monitor_stats': self.address_monitor.get_stats() if self.address_monitor else {},
                'active_addresses': len(self.db.get_all_active_addresses()),
                'timestamp': datetime.now()
            }
            
            # 这里可以生成详细的统计报告
            # 可以发送给管理员或保存到文件
            
            logger.info(f"统计报告生成完成 - 活跃地址: {stats_data['active_addresses']}, "
                       f"总任务执行: {self.stats['total_tasks_executed']}")
            
        except Exception as e:
            logger.error(f"生成统计报告任务失败: {e}")
            self.stats['failed_tasks'] += 1
    
    def get_scheduler_stats(self) -> dict:
        """获取调度器统计信息"""
        return {
            **self.stats,
            'is_running': self.is_running,
            'active_jobs': len(self.scheduler.get_jobs()) if self.scheduler else 0,
            'scheduled_jobs': [job.name for job in self.scheduler.get_jobs()] if self.scheduler else []
        }


class TaskManager:
    """任务管理器 - 统一管理所有后台任务"""
    
    def __init__(self):
        self.database = None
        self.telegram_bot = None
        self.scheduler = None
        self.is_initialized = False
    
    async def initialize(self, telegram_token: str):
        """初始化任务管理器"""
        try:
            logger.info("初始化任务管理器...")
            
            # 验证配置
            Config.validate()
            
            # 初始化数据库
            self.database = DatabaseManager(Config.DATABASE_PATH)
            
            # 初始化Telegram机器人
            self.telegram_bot = TelegramBot(telegram_token, self.database)
            await self.telegram_bot.run()
            
            # 等待机器人完全启动
            while not self.telegram_bot.application:
                await asyncio.sleep(1)
            
            # 初始化调度器
            self.scheduler = TaskScheduler(self.database, self.telegram_bot)
            await self.scheduler.initialize()
            
            self.is_initialized = True
            logger.info("任务管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化任务管理器失败: {e}")
            raise
    
    async def run(self):
        """运行任务管理器"""
        if not self.is_initialized:
            raise RuntimeError("任务管理器未初始化")
        
        try:
            logger.info("启动任务管理器...")
            
            # 启动调度器
            await self.scheduler.start()
            
        except Exception as e:
            logger.error(f"任务管理器运行失败: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("清理任务管理器资源...")
            
            # 停止调度器
            if self.scheduler:
                await self.scheduler.shutdown()
            
            # 停止Telegram机器人
            if self.telegram_bot and self.telegram_bot.application:
                await self.telegram_bot.application.stop()
            
            logger.info("任务管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
    
    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            'initialized': self.is_initialized,
            'database': self.database is not None,
            'telegram_bot': self.telegram_bot is not None,
            'scheduler': self.scheduler is not None,
            'scheduler_stats': self.scheduler.get_scheduler_stats() if self.scheduler else None
        }