import logging
import re
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

from config import Config
from database import DatabaseManager
from data_fetcher import HyperliquidDataFetcher
from message_formatter import MessageFormatter

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram机器人 - 负责用户交互和命令处理"""
    
    def __init__(self, token: str, database: DatabaseManager):
        self.token = token
        self.db = database
        self.data_fetcher = HyperliquidDataFetcher()
        self.message_formatter = MessageFormatter()
        self.application = None
        
        # 命令前缀
        self.COMMANDS = {
            'start': self.start_command,
            'help': self.help_command,
            'add': self.add_address_command,
            'remove': self.remove_address_command,
            'list': self.list_addresses_command,
            'setinterval': self.set_interval_command,
            'status': self.status_command,
            'test': self.test_command
        }
    
    def is_valid_address(self, address: str) -> bool:
        """验证以太坊地址格式"""
        # 检查地址格式：0x开头，40位十六进制字符
        pattern = r'^0x[a-fA-F0-9]{40}$'
        return bool(re.match(pattern, address))
    
    def extract_address_from_text(self, text: str) -> str:
        """从文本中提取以太坊地址"""
        # 匹配0x开头的40位十六进制字符
        pattern = r'0x[a-fA-F0-9]{40}'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start命令处理"""
        user = update.effective_user
        
        # 记录用户信息
        self.db.add_user(user.id, user.username)
        
        welcome_message = f"""
🤖 **Hypeliquid聪明钱监控机器人**

欢迎使用！我可以帮你监控Hypeliquid链上的聪明钱地址动态。

**可用命令：**
• `/add 0x地址 [标签]` - 添加监控地址
• `/remove 0x地址` - 移除监控地址
• `/list` - 查看监控列表
• `/setinterval 秒数` - 设置扫描间隔（默认60秒）
• `/status` - 查看机器人状态
• `/help` - 显示帮助信息

**示例：**
`/add 0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae 聪明钱1`

开始监控聪明钱的链上动态吧！🚀
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help命令处理"""
        help_message = """
📋 **使用帮助**

**核心功能：**
• 监控Hypeliquid链上地址动态
• 实时推送交易和资产变动
• 支持多个地址同时监控
• 可自定义扫描频率

**命令详解：**

1️⃣ **添加监控地址**
   `/add 0x地址 [标签]`
   示例: `/add 0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae 聪明钱1`

2️⃣ **移除监控地址**
   `/remove 0x地址`
   示例: `/remove 0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae`

3️⃣ **查看监控列表**
   `/list` - 显示当前监控的所有地址

4️⃣ **设置扫描间隔**
   `/setinterval 秒数` (最小30秒，最大3600秒)
   示例: `/setinterval 120` (2分钟扫描一次)

5️⃣ **查看状态**
   `/status` - 显示机器人运行状态

**注意事项：**
• 每个用户最多监控20个地址
• 地址必须是有效的以太坊格式
• 扫描频率越高，通知越及时，但API消耗越大
        """
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def add_address_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/add命令处理"""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "❌ 请提供要监控的地址\n"
                "示例: `/add 0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae 聪明钱1`",
                parse_mode='Markdown'
            )
            return
        
        # 提取地址和标签
        full_text = ' '.join(context.args)
        address = self.extract_address_from_text(full_text)
        
        if not address:
            await update.message.reply_text(
                "❌ 未找到有效的以太坊地址\n"
                "请确保地址格式正确：0x开头，40位十六进制字符"
            )
            return
        
        # 提取标签（地址后面的文字）
        label = full_text.replace(address, '').strip() or None
        
        # 验证地址格式
        if not self.is_valid_address(address):
            await update.message.reply_text("❌ 地址格式无效，请检查")
            return
        
        # 检查用户地址数量限制
        user_addresses = self.db.get_user_addresses(user.id)
        if len(user_addresses) >= Config.MAX_ADDRESSES_PER_USER:
            await update.message.reply_text(
                f"❌ 每个用户最多监控 {Config.MAX_ADDRESSES_PER_USER} 个地址\n"
                f"请先移除一些地址再添加新的"
            )
            return
        
        # 添加地址到数据库
        if self.db.add_monitored_address(user.id, address, label):
            # 获取地址当前状态（用于后续对比）
            address_state = await self.data_fetcher.get_address_state(address)
            if address_state:
                self.db.update_address_state(address, address_state)
            
            response_text = f"""
✅ **地址添加成功**

地址：`{address}`
{f'标签：{label}' if label else ''}

机器人将开始监控此地址的链上动态。
使用 `/list` 查看所有监控地址。
            """
            
            await update.message.reply_text(response_text, parse_mode='Markdown')
            logger.info(f"用户 {user.id} 添加监控地址: {address}")
        else:
            await update.message.reply_text("❌ 添加地址失败，请重试")
    
    async def remove_address_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/remove命令处理"""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "❌ 请提供要移除的地址\n"
                "示例: `/remove 0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae`",
                parse_mode='Markdown'
            )
            return
        
        # 提取地址
        full_text = ' '.join(context.args)
        address = self.extract_address_from_text(full_text)
        
        if not address:
            await update.message.reply_text("❌ 未找到有效的以太坊地址")
            return
        
        # 验证地址格式
        if not self.is_valid_address(address):
            await update.message.reply_text("❌ 地址格式无效")
            return
        
        # 检查地址是否在监控列表中
        user_addresses = self.db.get_user_addresses(user.id)
        address_exists = any(addr['address'] == address.lower() for addr in user_addresses)
        
        if not address_exists:
            await update.message.reply_text("❌ 该地址不在您的监控列表中")
            return
        
        # 从数据库移除地址
        if self.db.remove_monitored_address(user.id, address):
            await update.message.reply_text(f"✅ 地址已移除：`{address}`", parse_mode='Markdown')
            logger.info(f"用户 {user.id} 移除监控地址: {address}")
        else:
            await update.message.reply_text("❌ 移除地址失败，请重试")
    
    async def list_addresses_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/list命令处理"""
        user = update.effective_user
        
        addresses = self.db.get_user_addresses(user.id)
        
        if not addresses:
            await update.message.reply_text(
                "📭 您当前没有监控任何地址\n"
                "使用 `/add 0x地址` 开始添加监控地址",
                parse_mode='Markdown'
            )
            return
        
        # 构建地址列表消息
        message = "📋 **您的监控地址列表**\n\n"
        
        for i, addr in enumerate(addresses, 1):
            label = addr['label'] or '未命名'
            address_short = f"{addr['address'][:6]}...{addr['address'][-4:]}"
            last_scan = addr['last_scan'] or '从未扫描'
            
            message += f"{i}. **{label}**\n"
            message += f"   地址：`{address_short}`\n"
            message += f"   上次扫描：{last_scan}\n\n"
        
        message += f"共监控 **{len(addresses)}** 个地址"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def set_interval_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/setinterval命令处理"""
        user = update.effective_user
        
        if not context.args:
            current_interval = self.db.get_user_scan_interval(user.id)
            await update.message.reply_text(
                f"⏱ 当前扫描间隔：{current_interval} 秒\n"
                f"使用 `/setinterval 120` 设置为2分钟\n"
                f"（建议范围：60-300秒）"
            )
            return
        
        try:
            interval = int(context.args[0])
            
            # 验证范围
            if interval < 30 or interval > 3600:
                await update.message.reply_text(
                    "❌ 扫描间隔必须在30-3600秒之间\n"
                    "建议范围：60-300秒"
                )
                return
            
            # 更新数据库
            if self.db.update_user_scan_interval(user.id, interval):
                await update.message.reply_text(f"✅ 扫描间隔已设置为：{interval} 秒")
                logger.info(f"用户 {user.id} 设置扫描间隔: {interval} 秒")
            else:
                await update.message.reply_text("❌ 设置失败，请重试")
                
        except ValueError:
            await update.message.reply_text("❌ 请输入有效的数字（秒数）")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/status命令处理"""
        user = update.effective_user
        
        addresses = self.db.get_user_addresses(user.id)
        scan_interval = self.db.get_user_scan_interval(user.id)
        
        # 获取系统状态
        all_addresses = self.db.get_all_active_addresses()
        
        status_message = f"""
📊 **机器人状态**

**您的统计：**
• 监控地址数：{len(addresses)}
• 扫描间隔：{scan_interval} 秒

**系统统计：**
• 总监控地址数：{len(all_addresses)}
• 机器人运行状态：正常 ✅
• 数据库状态：正常 ✅

**功能状态：**
• 地址监控：✅ 启用
• 交易检测：✅ 启用
• 消息推送：✅ 启用
        """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/test命令处理（测试通知）"""
        user = update.effective_user
        
        # 获取用户的一个监控地址进行测试
        addresses = self.db.get_user_addresses(user.id)
        
        if not addresses:
            await update.message.reply_text("❌ 请先添加监控地址再进行测试")
            return
        
        test_address = addresses[0]['address']
        
        # 模拟一条测试通知
        test_message = self.message_formatter.format_notification({
            'address': test_address,
            'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
            'tx_type': 'transfer',
            'amount': '1000',
            'token_symbol': 'USDC',
            'timestamp': '2025-10-28 14:32:05',
            'is_test': True
        })
        
        await update.message.reply_text(test_message, parse_mode='Markdown')
    
    async def handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理未知命令"""
        await update.message.reply_text(
            "❓ 未知命令\n"
            "使用 `/help` 查看可用命令",
            parse_mode='Markdown'
        )
    
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """错误处理"""
        logger.error(f"更新 {update} 导致错误 {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ 处理请求时出现错误，请稍后重试"
                )
            except TelegramError:
                pass  # 忽略发送错误消息时的异常
    
    def setup_handlers(self):
        """设置命令处理器"""
        # 添加命令处理器
        for command, handler in self.COMMANDS.items():
            self.application.add_handler(CommandHandler(command, handler))
        
        # 添加未知命令处理器
        self.application.add_handler(MessageHandler(filters.COMMAND, self.handle_unknown_command))
        
        # 添加错误处理器
        self.application.add_error_handler(self.handle_error)
    
    async def run(self):
        """运行机器人"""
        try:
            # 创建应用
            self.application = Application.builder().token(self.token).build()
            
            # 设置处理器
            self.setup_handlers()
            
            # 启动机器人
            logger.info("Telegram机器人启动中...")
            await self.application.initialize()
            await self.application.start()
            
            logger.info("Telegram机器人已启动")
            
        except Exception as e:
            logger.error(f"机器人启动失败: {e}")
            raise