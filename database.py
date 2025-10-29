import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器 - 负责所有数据持久化操作"""
    
    def __init__(self, db_path: str):
        self.db_path = self._validate_db_path(db_path)
        self.init_database()
    
    def _validate_db_path(self, db_path: str) -> str:
        """验证数据库路径安全性，防止路径遍历攻击"""
        try:
            # 先检查原始路径中的危险模式，在标准化之前
            original_path = db_path.strip()
            
            # 禁止路径遍历字符序列（在标准化之前检查）
            if '..' in original_path or '//' in original_path or '\\\\' in original_path:
                raise ValueError(f"数据库路径包含非法字符序列: {original_path}")
            
            # 标准化路径
            db_path = os.path.normpath(original_path)
            
            # 禁止绝对路径，只允许相对路径
            if os.path.isabs(db_path):
                raise ValueError(f"数据库路径不允许使用绝对路径: {db_path}")
            
            # 只允许安全的文件名字符（字母、数字、下划线、连字符、点）
            filename = os.path.basename(db_path)
            if not filename.replace('.', '').replace('-', '').replace('_', '').isalnum():
                raise ValueError(f"数据库文件名包含非法字符: {filename}")
            
            # 确保目录存在
            db_dir = os.path.dirname(db_path) or '.'
            os.makedirs(db_dir, exist_ok=True)
            
            # 验证最终路径是否安全
            abs_path = os.path.abspath(db_path)
            current_dir = os.getcwd()
            
            # 确保数据库文件在当前工作目录或其子目录下
            if not abs_path.startswith(current_dir):
                raise ValueError(f"数据库路径必须位于当前工作目录下: {db_path}")
            
            logger.info(f"数据库路径验证通过: {db_path}")
            return db_path
            
        except Exception as e:
            logger.error(f"数据库路径验证失败: {e}")
            raise ValueError(f"数据库路径不安全: {e}")
    
    def init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    scan_interval INTEGER DEFAULT 60
                )
            ''')
            
            # 监控地址表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitored_addresses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    address TEXT NOT NULL,
                    label TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_scan TIMESTAMP,
                    last_tx_hash TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, address)
                )
            ''')
            
            # 地址状态表（存储上次扫描时的状态）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS address_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    balance TEXT,
                    transaction_count INTEGER,
                    last_tx_hash TEXT,
                    last_tx_time TIMESTAMP,
                    state_data TEXT,  -- JSON格式的完整状态
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(address)
                )
            ''')
            
            # 交易历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    tx_hash TEXT NOT NULL,
                    tx_type TEXT,  -- 'buy', 'sell', 'transfer'
                    amount TEXT,
                    token_symbol TEXT,
                    from_address TEXT,
                    to_address TEXT,
                    block_number INTEGER,
                    timestamp TIMESTAMP,
                    gas_used INTEGER,
                    gas_price TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tx_hash)
                )
            ''')
            
            # 通知记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    address TEXT NOT NULL,
                    tx_hash TEXT NOT NULL,
                    notification_type TEXT,
                    message TEXT,
                    is_sent BOOLEAN DEFAULT 0,
                    sent_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
            logger.info("数据库表结构初始化完成")
    
    def add_user(self, user_id: int, username: str = None) -> bool:
        """添加新用户"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, last_activity)
                    VALUES (?, ?, ?)
                ''', (user_id, username, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"添加用户失败: {e}")
            return False
    
    def add_monitored_address(self, user_id: int, address: str, label: str = None) -> bool:
        """添加监控地址"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO monitored_addresses (user_id, address, label)
                    VALUES (?, ?, ?)
                ''', (user_id, address.lower(), label))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"添加监控地址失败: {e}")
            return False
    
    def remove_monitored_address(self, user_id: int, address: str) -> bool:
        """移除监控地址"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE monitored_addresses 
                    SET is_active = 0 
                    WHERE user_id = ? AND address = ?
                ''', (user_id, address.lower()))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"移除监控地址失败: {e}")
            return False
    
    def get_user_addresses(self, user_id: int) -> List[Dict]:
        """获取用户的所有监控地址"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM monitored_addresses 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                addresses = []
                for row in cursor.fetchall():
                    addresses.append(dict(row))
                return addresses
        except Exception as e:
            logger.error(f"获取用户地址失败: {e}")
            return []
    
    def get_all_active_addresses(self) -> List[str]:
        """获取所有活跃的监控地址（用于批量扫描）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT address FROM monitored_addresses 
                    WHERE is_active = 1
                ''')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取活跃地址失败: {e}")
            return []
    
    def get_address_state(self, address: str) -> Optional[Dict]:
        """获取地址的上次状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM address_states 
                    WHERE address = ?
                ''', (address.lower(),))
                
                row = cursor.fetchone()
                if row:
                    state = dict(row)
                    if state['state_data']:
                        state['state_data'] = json.loads(state['state_data'])
                    return state
                return None
        except Exception as e:
            logger.error(f"获取地址状态失败: {e}")
            return None
    
    def update_address_state(self, address: str, state_data: Dict) -> bool:
        """更新地址状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO address_states 
                    (address, balance, transaction_count, last_tx_hash, last_tx_time, state_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    address.lower(),
                    state_data.get('balance'),
                    state_data.get('transaction_count', 0),
                    state_data.get('last_tx_hash'),
                    state_data.get('last_tx_time'),
                    json.dumps(state_data) if state_data else None
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"更新地址状态失败: {e}")
            return False
    
    def add_transaction(self, tx_data: Dict) -> bool:
        """添加交易记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO transactions 
                    (address, tx_hash, tx_type, amount, token_symbol, from_address, to_address,
                     block_number, timestamp, gas_used, gas_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tx_data['address'].lower(),
                    tx_data['tx_hash'],
                    tx_data.get('tx_type'),
                    tx_data.get('amount'),
                    tx_data.get('token_symbol'),
                    tx_data.get('from_address'),
                    tx_data.get('to_address'),
                    tx_data.get('block_number'),
                    tx_data.get('timestamp'),
                    tx_data.get('gas_used'),
                    tx_data.get('gas_price')
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"添加交易记录失败: {e}")
            return False
    
    def add_notification(self, user_id: int, address: str, tx_hash: str, 
                        notification_type: str, message: str) -> bool:
        """添加通知记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notifications 
                    (user_id, address, tx_hash, notification_type, message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, address.lower(), tx_hash, notification_type, message))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"添加通知记录失败: {e}")
            return False
    
    def get_pending_notifications(self, limit: int = 100) -> List[Dict]:
        """获取待发送的通知"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM notifications 
                    WHERE is_sent = 0 
                    ORDER BY created_at ASC
                    LIMIT ?
                ''', (limit,))
                
                notifications = []
                for row in cursor.fetchall():
                    notifications.append(dict(row))
                return notifications
        except Exception as e:
            logger.error(f"获取待发送通知失败: {e}")
            return []
    
    def mark_notification_sent(self, notification_id: int) -> bool:
        """标记通知为已发送"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE notifications 
                    SET is_sent = 1, sent_at = ?
                    WHERE id = ?
                ''', (datetime.now(), notification_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新通知状态失败: {e}")
            return False
    
    def update_user_scan_interval(self, user_id: int, interval: int) -> bool:
        """更新用户扫描间隔"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET scan_interval = ?
                    WHERE user_id = ?
                ''', (interval, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新扫描间隔失败: {e}")
            return False
    
    def get_user_scan_interval(self, user_id: int) -> int:
        """获取用户扫描间隔"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT scan_interval FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else 60  # 默认60秒
        except Exception as e:
            logger.error(f"获取用户扫描间隔失败: {e}")
            return 60
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """清理旧数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 验证输入参数，防止负数或过大的值
                if (not isinstance(days_to_keep, int) or isinstance(days_to_keep, bool) or 
                    days_to_keep < 1 or days_to_keep > 365):
                    logger.error(f"无效的清理天数参数: {days_to_keep}")
                    return False
                
                # 使用参数化查询，避免SQL注入
                # SQLite不支持参数化间隔表达式，使用安全的日期计算
                cursor.execute('''
                    DELETE FROM transactions 
                    WHERE created_at < datetime('now', ?)
                ''', (f'-{days_to_keep} days',))
                
                deleted_transactions = cursor.rowcount
                
                # 清理旧的通知记录
                cursor.execute('''
                    DELETE FROM notifications 
                    WHERE created_at < datetime('now', ?)
                ''', (f'-{days_to_keep} days',))
                
                deleted_notifications = cursor.rowcount
                
                conn.commit()
                logger.info(f"数据清理完成，删除了 {deleted_transactions} 条交易记录和 {deleted_notifications} 条通知记录")
                return True
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return False