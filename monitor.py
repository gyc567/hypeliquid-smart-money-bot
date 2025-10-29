import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime, timedelta
import time

from config import Config
from database import DatabaseManager
from data_fetcher import HyperliquidDataFetcher
from message_formatter import MessageFormatter

logger = logging.getLogger(__name__)

class AddressMonitor:
    """地址监控器 - 负责扫描地址变化并触发通知"""
    
    def __init__(self, database: DatabaseManager):
        self.db = database
        self.data_fetcher = HyperliquidDataFetcher()
        self.message_formatter = MessageFormatter()
        self.is_running = False
        self.monitor_task = None
        
        # 统计信息
        self.stats = {
            'total_scans': 0,
            'addresses_found_changes': 0,
            'notifications_sent': 0,
            'errors': 0,
            'last_scan_time': None
        }
    
    async def start_monitoring(self):
        """开始监控循环"""
        if self.is_running:
            logger.warning("监控器已经在运行中")
            return
        
        self.is_running = True
        logger.info("地址监控器启动")
        
        try:
            async with self.data_fetcher:
                while self.is_running:
                    try:
                        await self._scan_cycle()
                        
                        # 等待下一次扫描
                        await asyncio.sleep(10)  # 基础间隔10秒，具体间隔由用户设置决定
                        
                    except Exception as e:
                        logger.error(f"扫描循环出错: {e}")
                        self.stats['errors'] += 1
                        await asyncio.sleep(30)  # 出错后等待30秒再重试
                        
        except Exception as e:
            logger.error(f"监控器运行失败: {e}")
            self.is_running = False
    
    async def stop_monitoring(self):
        """停止监控循环"""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
        logger.info("地址监控器停止")
    
    async def _scan_cycle(self):
        """执行一次完整的扫描周期"""
        start_time = time.time()
        
        try:
            # 获取所有需要扫描的地址
            active_addresses = self.db.get_all_active_addresses()
            
            if not active_addresses:
                logger.debug("没有活跃的监控地址")
                return
            
            logger.info(f"开始扫描 {len(active_addresses)} 个地址")
            
            # 按用户分组处理，每个用户有自己的扫描间隔
            user_addresses = self._group_addresses_by_user(active_addresses)
            
            # 并行处理不同用户的地址
            tasks = []
            for user_id, addresses in user_addresses.items():
                task = asyncio.create_task(
                    self._scan_user_addresses(user_id, addresses)
                )
                tasks.append(task)
            
            # 等待所有扫描完成
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 更新统计
            self.stats['total_scans'] += 1
            self.stats['last_scan_time'] = datetime.now()
            
            scan_duration = time.time() - start_time
            logger.info(f"扫描完成，耗时: {scan_duration:.2f}秒")
            
        except Exception as e:
            logger.error(f"扫描周期失败: {e}")
            self.stats['errors'] += 1
    
    def _group_addresses_by_user(self, addresses: List[str]) -> Dict[int, List[str]]:
        """按用户ID分组地址"""
        user_addresses = {}
        
        for address in addresses:
            # 获取监控此地址的用户
            # 这里简化处理，实际应该查询数据库获取地址对应的用户
            # 暂时假设所有地址都属于系统用户
            user_id = 1  # 默认用户ID
            
            if user_id not in user_addresses:
                user_addresses[user_id] = []
            user_addresses[user_id].append(address)
        
        return user_addresses
    
    async def _scan_user_addresses(self, user_id: int, addresses: List[str]):
        """扫描单个用户的地址"""
        try:
            # 获取用户的扫描间隔
            scan_interval = self.db.get_user_scan_interval(user_id)
            
            # 检查是否需要扫描（基于上次扫描时间）
            should_scan = await self._should_scan_address(addresses[0], scan_interval)
            if not should_scan:
                return
            
            # 并行扫描地址
            tasks = []
            for address in addresses:
                task = asyncio.create_task(self._scan_single_address(address))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理扫描结果
            for address, result in zip(addresses, results):
                if isinstance(result, Exception):
                    logger.error(f"扫描地址 {address} 失败: {result}")
                    continue
                
                if result and result['has_changes']:
                    await self._handle_address_changes(user_id, address, result['changes'])
            
        except Exception as e:
            logger.error(f"扫描用户 {user_id} 地址失败: {e}")
    
    async def _should_scan_address(self, address: str, scan_interval: int) -> bool:
        """判断是否应该扫描地址（基于间隔时间）"""
        try:
            # 获取地址的上次扫描时间
            address_info = self.db.get_address_state(address)
            
            if not address_info:
                return True  # 从未扫描过
            
            last_scan = address_info.get('scan_time')
            if not last_scan:
                return True
            
            # 解析上次扫描时间
            try:
                last_scan_time = datetime.fromisoformat(last_scan)
            except:
                return True
            
            # 检查是否到了下次扫描时间
            next_scan_time = last_scan_time + timedelta(seconds=scan_interval)
            return datetime.now() >= next_scan_time
            
        except Exception as e:
            logger.error(f"判断扫描时间失败 {address}: {e}")
            return True  # 出错时默认扫描
    
    async def _scan_single_address(self, address: str) -> Dict:
        """扫描单个地址"""
        try:
            logger.debug(f"扫描地址: {address}")
            
            # 获取当前状态
            current_state = await self.data_fetcher.get_address_state(address)
            if not current_state:
                logger.warning(f"无法获取地址状态: {address}")
                return {'has_changes': False, 'changes': []}
            
            # 获取上次状态
            old_state = self.db.get_address_state(address)
            
            # 检测变化
            changes = await self.data_fetcher.detect_address_changes(address, old_state, current_state)
            
            # 更新数据库中的状态
            self.db.update_address_state(address, current_state)
            
            # 更新地址的最后扫描时间
            self._update_address_last_scan(address)
            
            return {
                'has_changes': len(changes) > 0,
                'changes': changes,
                'old_state': old_state,
                'new_state': current_state
            }
            
        except Exception as e:
            logger.error(f"扫描地址 {address} 失败: {e}")
            return {'has_changes': False, 'changes': []}
    
    def _update_address_last_scan(self, address: str):
        """更新地址的最后扫描时间"""
        try:
            # 这里简化处理，实际应该更新数据库
            logger.debug(f"更新地址 {address} 的最后扫描时间")
        except Exception as e:
            logger.error(f"更新地址扫描时间失败 {address}: {e}")
    
    async def _handle_address_changes(self, user_id: int, address: str, changes: List[Dict]):
        """处理地址变化，生成通知"""
        try:
            logger.info(f"地址 {address} 检测到 {len(changes)} 个变化")
            self.stats['addresses_found_changes'] += 1
            
            # 为每个变化生成通知
            for change in changes:
                await self._create_notification(user_id, address, change)
                
        except Exception as e:
            logger.error(f"处理地址变化失败 {address}: {e}")
    
    async def _create_notification(self, user_id: int, address: str, change: Dict):
        """创建通知记录"""
        try:
            # 格式化通知消息
            message = self.message_formatter.format_change_notification(address, change)
            
            # 根据变化类型确定通知类型
            notification_type = change.get('type', 'unknown')
            
            # 获取相关的交易哈希（如果有）
            tx_hash = change.get('tx_hash', '')
            
            # 添加到数据库
            success = self.db.add_notification(
                user_id=user_id,
                address=address,
                tx_hash=tx_hash,
                notification_type=notification_type,
                message=message
            )
            
            if success:
                logger.info(f"创建通知成功: {address} - {notification_type}")
            else:
                logger.error(f"创建通知失败: {address}")
                
        except Exception as e:
            logger.error(f"创建通知失败 {address}: {e}")
    
    def get_stats(self) -> Dict:
        """获取监控统计信息"""
        return {
            **self.stats,
            'is_running': self.is_running,
            'uptime': self._get_uptime()
        }
    
    def _get_uptime(self) -> str:
        """获取运行时间"""
        if not self.stats['last_scan_time']:
            return "未开始"
        
        # 这里简化处理，实际应该记录启动时间
        return "运行中"
    
    async def force_scan_address(self, address: str) -> Dict:
        """强制扫描特定地址（用于测试）"""
        try:
            logger.info(f"强制扫描地址: {address}")
            
            result = await self._scan_single_address(address)
            
            if result['has_changes']:
                logger.info(f"强制扫描发现 {len(result['changes'])} 个变化")
            else:
                logger.info("强制扫描未发现变化")
            
            return result
            
        except Exception as e:
            logger.error(f"强制扫描失败 {address}: {e}")
            return {'has_changes': False, 'changes': [], 'error': str(e)}


class NotificationProcessor:
    """通知处理器 - 负责发送待处理的通知"""
    
    def __init__(self, database: DatabaseManager, bot_application):
        self.db = database
        self.bot_application = bot_application
        self.message_formatter = MessageFormatter()
        self.is_running = False
    
    async def start_processing(self):
        """开始处理通知"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("通知处理器启动")
        
        try:
            while self.is_running:
                try:
                    await self._process_pending_notifications()
                    await asyncio.sleep(5)  # 每5秒检查一次
                    
                except Exception as e:
                    logger.error(f"通知处理出错: {e}")
                    await asyncio.sleep(10)  # 出错后等待10秒
                    
        except Exception as e:
            logger.error(f"通知处理器停止: {e}")
            self.is_running = False
    
    async def stop_processing(self):
        """停止处理通知"""
        self.is_running = False
        logger.info("通知处理器停止")
    
    async def _process_pending_notifications(self):
        """处理待发送的通知"""
        try:
            # 获取待发送的通知
            pending_notifications = self.db.get_pending_notifications(limit=50)
            
            if not pending_notifications:
                return
            
            logger.info(f"处理 {len(pending_notifications)} 个待发送通知")
            
            # 发送通知
            for notification in pending_notifications:
                try:
                    await self._send_notification(notification)
                    
                    # 标记为已发送
                    self.db.mark_notification_sent(notification['id'])
                    
                except Exception as e:
                    logger.error(f"发送通知失败 {notification['id']}: {e}")
                    # 不标记为已发送，下次会重试
                    
        except Exception as e:
            logger.error(f"处理待发送通知失败: {e}")
    
    async def _send_notification(self, notification: Dict):
        """发送单个通知"""
        try:
            user_id = notification['user_id']
            message = notification['message']
            
            # 通过 Telegram Bot 发送消息
            await self.bot_application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"通知发送成功: 用户 {user_id}")
            
        except Exception as e:
            logger.error(f"发送通知消息失败: {e}")
            raise  # 重新抛出异常，让上层处理