import logging
from datetime import datetime
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class MessageFormatter:
    """消息格式化器 - 负责格式化推送消息"""
    
    def __init__(self):
        # 交易类型对应的表情符号
        self.tx_emojis = {
            'buy': '🟢',
            'sell': '🔴',
            'transfer': '🔄',
            'receive': '💰',
            'unknown': '❓'
        }
        
        # 变化类型对应的表情符号
        self.change_emojis = {
            'balance_increase': '📈',
            'balance_decrease': '📉',
            'new_transaction': '🔄',
            'initial_monitor': '🔍',
            'unknown': '❓'
        }
        
        # 通知类型对应的图标
        self.notification_icons = {
            'balance_change': '💰',
            'new_transaction': '🔄',
            'large_transaction': '🚨',
            'initial_monitor': '🔍',
            'test': '🧪'
        }
    
    def format_change_notification(self, address: str, change: Dict) -> str:
        """格式化变化通知"""
        try:
            change_type = change.get('type', 'unknown')
            emoji = self.change_emojis.get(change_type, '❓')
            
            # 地址缩写
            address_short = self._format_address(address)
            
            if change_type == 'initial_monitor':
                return self._format_initial_monitor(address_short, change)
            
            elif change_type == 'balance_increase':
                return self._format_balance_increase(address_short, change)
            
            elif change_type == 'balance_decrease':
                return self._format_balance_decrease(address_short, change)
            
            elif change_type == 'new_transaction':
                return self._format_new_transaction(address_short, change)
            
            else:
                return self._format_unknown_change(address_short, change)
                
        except Exception as e:
            logger.error(f"格式化变化通知失败: {e}")
            return self._format_error_notification(address, change)
    
    def _format_initial_monitor(self, address_short: str, change: Dict) -> str:
        """格式化初始监控通知"""
        balance = change.get('balance', '0')
        tx_count = change.get('transaction_count', 0)
        
        return f"""
🔍 **开始监控地址**

地址：`{address_short}`
余额：{float(balance):.4f} ETH
交易数：{tx_count}

机器人将实时监控此地址的链上动态。
        """.strip()
    
    def _format_balance_increase(self, address_short: str, change: Dict) -> str:
        """格式化余额增加通知"""
        old_balance = float(change.get('old_balance', '0'))
        new_balance = float(change.get('new_balance', '0'))
        change_amount = float(change.get('change_amount', '0'))
        
        # 计算百分比变化
        if old_balance > 0:
            percent_change = (change_amount / old_balance) * 100
            percent_str = f" (+{percent_change:.1f}%)"
        else:
            percent_str = ""
        
        return f"""
📈 **余额增加**

地址：`{address_short}`
变化：+{change_amount:.4f} ETH{percent_str}
余额：{old_balance:.4f} → {new_balance:.4f} ETH

💰 地址收到资金，可能是聪明钱操作。
        """.strip()
    
    def _format_balance_decrease(self, address_short: str, change: Dict) -> str:
        """格式化余额减少通知"""
        old_balance = float(change.get('old_balance', '0'))
        new_balance = float(change.get('new_balance', '0'))
        change_amount = float(change.get('change_amount', '0'))
        
        # 计算百分比变化
        if old_balance > 0:
            percent_change = (change_amount / old_balance) * 100
            percent_str = f" (-{percent_change:.1f}%)"
        else:
            percent_str = ""
        
        return f"""
📉 **余额减少**

地址：`{address_short}`
变化：-{change_amount:.4f} ETH{percent_str}
余额：{old_balance:.4f} → {new_balance:.4f} ETH

💸 地址转出资金，关注其投资动向。
        """.strip()
    
    def _format_new_transaction(self, address_short: str, change: Dict) -> str:
        """格式化新交易通知"""
        tx_type = change.get('tx_type', 'unknown')
        emoji = self.tx_emojis.get(tx_type, '❓')
        amount = float(change.get('amount', '0'))
        tx_hash = change.get('tx_hash', '')
        block_number = change.get('block_number', 0)
        
        # 交易类型描述
        tx_type_desc = self._get_transaction_description(tx_type)
        
        # 交易哈希缩写
        tx_hash_short = self._format_tx_hash(tx_hash)
        
        # 构建查看链接
        tx_link = f"https://hypurrscan.io/tx/{tx_hash}" if tx_hash else ""
        
        message = f"""
{emoji} **新交易 - {tx_type_desc}**

地址：`{address_short}`
金额：{amount:.4f} ETH
哈希：`{tx_hash_short}`
区块：#{block_number}
        """.strip()
        
        if tx_link:
            message += f"\n🔗 [查看详情]({tx_link})"
        
        return message
    
    def _format_unknown_change(self, address_short: str, change: Dict) -> str:
        """格式化未知变化通知"""
        message = change.get('message', '检测到未知变化')
        
        return f"""
❓ **地址变化**

地址：`{address_short}`
描述：{message}
        """.strip()
    
    def _format_error_notification(self, address: str, change: Dict) -> str:
        """格式化错误通知"""
        address_short = self._format_address(address)
        
        return f"""
⚠️ **通知格式化错误**

地址：`{address_short}`
状态：无法格式化通知内容
        """.strip()
    
    def format_notification(self, notification_data: Dict) -> str:
        """格式化通用通知"""
        try:
            # 如果是测试通知
            if notification_data.get('is_test'):
                return self._format_test_notification(notification_data)
            
            # 提取基本信息
            address = notification_data.get('address', '')
            tx_hash = notification_data.get('tx_hash', '')
            tx_type = notification_data.get('tx_type', 'unknown')
            amount = notification_data.get('amount', '0')
            token_symbol = notification_data.get('token_symbol', 'ETH')
            timestamp = notification_data.get('timestamp', '')
            
            # 地址和交易哈希格式化
            address_short = self._format_address(address)
            tx_hash_short = self._format_tx_hash(tx_hash)
            
            # 交易类型图标
            emoji = self.tx_emojis.get(tx_type, '❓')
            
            # 交易类型描述
            tx_type_desc = self._get_transaction_description(tx_type)
            
            # 构建消息
            message = f"""
{emoji} **聪明钱地址有新动态**

地址：`{address_short}`
类型：{tx_type_desc}
金额：{amount} {token_symbol}
时间：{timestamp}
哈希：`{tx_hash_short}`
            """.strip()
            
            # 添加查看链接
            if tx_hash:
                tx_link = f"https://hypurrscan.io/tx/{tx_hash}"
                message += f"\n🔗 [查看详情]({tx_link})"
            
            return message
            
        except Exception as e:
            logger.error(f"格式化通知失败: {e}")
            return self._format_error_notification(
                notification_data.get('address', ''), 
                notification_data
            )
    
    def _format_test_notification(self, notification_data: Dict) -> str:
        """格式化测试通知"""
        address = notification_data.get('address', '')
        address_short = self._format_address(address)
        
        return f"""
🧪 **测试通知**

地址：`{address_short}`
状态：这是一条测试消息

✅ 通知系统正常工作
        """.strip()
    
    def format_summary_report(self, summary_data: Dict) -> str:
        """格式化汇总报告"""
        try:
            total_addresses = summary_data.get('total_addresses', 0)
            active_addresses = summary_data.get('active_addresses', 0)
            total_changes = summary_data.get('total_changes', 0)
            scan_duration = summary_data.get('scan_duration', 0)
            
            # 计算变化率
            change_rate = (total_changes / active_addresses * 100) if active_addresses > 0 else 0
            
            return f"""
📊 **监控汇总报告**

**统计信息：**
• 总监控地址：{total_addresses}
• 活跃地址：{active_addresses}
• 检测到变化：{total_changes}
• 变化率：{change_rate:.1f}%

**性能信息：**
• 扫描耗时：{scan_duration:.2f}秒
• 状态：正常 ✅

**时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
        except Exception as e:
            logger.error(f"格式化汇总报告失败: {e}")
            return "❌ 无法生成汇总报告"
    
    def format_error_message(self, error_type: str, error_details: str) -> str:
        """格式化错误消息"""
        return f"""
⚠️ **系统错误**

类型：{error_type}
详情：{error_details}

时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
    
    def format_help_message(self) -> str:
        """格式化帮助消息"""
        return """
📚 **机器人使用帮助**

**核心功能：**
• 实时监控Hypeliquid链上地址动态
• 自动检测余额变化和交易活动
• 支持多个地址同时监控
• 可自定义扫描频率

**常用命令：**
• `/add 0x地址 [标签]` - 添加监控地址
• `/remove 0x地址` - 移除监控地址
• `/list` - 查看监控列表
• `/setinterval 秒数` - 设置扫描间隔
• `/status` - 查看机器人状态
• `/help` - 显示此帮助信息

**通知类型：**
🔍 初始监控 - 新添加的监控地址
📈 余额增加 - 地址收到资金
📉 余额减少 - 地址转出资金
🔄 新交易 - 检测到新的链上交易

**注意事项：**
• 每个用户最多监控20个地址
• 扫描间隔建议设置为60-300秒
• 地址格式必须为有效的以太坊地址
        """.strip()
    
    def _format_address(self, address: str) -> str:
        """格式化地址显示"""
        if not address or len(address) < 10:
            return address
        
        return f"{address[:6]}...{address[-4:]}"
    
    def _format_tx_hash(self, tx_hash: str) -> str:
        """格式化交易哈希显示"""
        if not tx_hash or len(tx_hash) < 10:
            return tx_hash
        
        return f"{tx_hash[:8]}...{tx_hash[-6:]}"
    
    def _get_transaction_description(self, tx_type: str) -> str:
        """获取交易类型描述"""
        descriptions = {
            'buy': '买入',
            'sell': '卖出',
            'transfer': '转账',
            'receive': '接收',
            'unknown': '未知交易'
        }
        
        return descriptions.get(tx_type, '未知交易')
    
    def format_large_transaction_alert(self, tx_data: Dict, threshold: float = 10000) -> str:
        """格式化大额交易警报"""
        try:
            address = tx_data.get('address', '')
            amount = float(tx_data.get('amount', '0'))
            tx_hash = tx_data.get('tx_hash', '')
            tx_type = tx_data.get('tx_type', 'unknown')
            
            address_short = self._format_address(address)
            tx_hash_short = self._format_tx_hash(tx_hash)
            emoji = self.tx_emojis.get(tx_type, '❓')
            
            return f"""
🚨 **大额交易警报**

地址：`{address_short}`
金额：${amount:,.2f}
类型：{self._get_transaction_description(tx_type)}
哈希：`{tx_hash_short}`

⚠️ 检测到超过 ${threshold:,.0f} 的大额交易！
            """.strip()
            
        except Exception as e:
            logger.error(f"格式化大额交易警报失败: {e}")
            return "🚨 检测到异常大额交易"
    
    def format_market_movement_alert(self, movement_data: Dict) -> str:
        """格式化市场异动警报"""
        try:
            direction = movement_data.get('direction', 'unknown')
            magnitude = movement_data.get('magnitude', 0)
            affected_addresses = movement_data.get('affected_addresses', [])
            
            direction_emoji = '📈' if direction == 'up' else '📉'
            
            # 格式化受影响的地址
            address_list = []
            for addr in affected_addresses[:5]:  # 最多显示5个地址
                address_list.append(f"`{self._format_address(addr)}`")
            
            addresses_text = "\n".join(address_list)
            if len(affected_addresses) > 5:
                addresses_text += f"\n...还有 {len(affected_addresses) - 5} 个地址"
            
            return f"""
{direction_emoji} **市场异动警报**

方向：{direction}
幅度：{magnitude:.2f}%
影响地址数：{len(affected_addresses)}

**受影响的聪明钱地址：**
{addresses_text}

🔍 建议关注这些地址的后续动向
            """.strip()
            
        except Exception as e:
            logger.error(f"格式化市场异动警报失败: {e}")
            return "📊 检测到市场异常波动"
    
    def truncate_message(self, message: str, max_length: int = 4096) -> str:
        """截断消息以适应Telegram限制"""
        if len(message) <= max_length:
            return message
        
        # 保留重要部分，截断中间内容
        header_end = message.find('\n', 100)  # 找到第一个换行
        if header_end == -1:
            header_end = 100
        
        footer_start = max_length - 200
        
        header = message[:header_end]
        footer = message[footer_start:] if len(message) > footer_start else ""
        
        truncated = f"{header}\n\n...（内容过长，已截断）\n\n{footer}"
        
        # 确保最终长度符合要求
        if len(truncated) > max_length:
            truncated = truncated[:max_length-20] + "\n...（已截断）"
        
        return truncated