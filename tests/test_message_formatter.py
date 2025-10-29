import pytest
from datetime import datetime
from message_formatter import MessageFormatter

class TestMessageFormatter:
    """消息格式化器测试"""
    
    @pytest.fixture
    def formatter(self):
        """创建消息格式化器实例"""
        return MessageFormatter()
    
    def test_format_change_notification_initial_monitor(self, formatter):
        """测试初始监控通知格式化"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        change = {
            'type': 'initial_monitor',
            'balance': '1.5',
            'transaction_count': 10
        }
        
        result = formatter.format_change_notification(address, change)
        
        assert "🔍" in result  # 包含正确的表情符号
        assert "开始监控地址" in result
        assert "0x742d...f0bEb6" in result  # 地址被正确格式化
        assert "1.5 ETH" in result  # 余额信息
        assert "10" in result  # 交易数量
    
    def test_format_change_notification_balance_increase(self, formatter):
        """测试余额增加通知格式化"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        change = {
            'type': 'balance_increase',
            'old_balance': '1.0',
            'new_balance': '1.5',
            'change_amount': '0.5'
        }
        
        result = formatter.format_change_notification(address, change)
        
        assert "📈" in result  # 包含正确的表情符号
        assert "余额增加" in result
        assert "+0.5 ETH" in result  # 变化金额
        assert "1.0 → 1.5 ETH" in result  # 余额变化
    
    def test_format_change_notification_balance_decrease(self, formatter):
        """测试余额减少通知格式化"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        change = {
            'type': 'balance_decrease',
            'old_balance': '2.0',
            'new_balance': '1.5',
            'change_amount': '0.5'
        }
        
        result = formatter.format_change_notification(address, change)
        
        assert "📉" in result  # 包含正确的表情符号
        assert "余额减少" in result
        assert "-0.5 ETH" in result  # 变化金额
        assert "2.0 → 1.5 ETH" in result  # 余额变化
    
    def test_format_change_notification_new_transaction(self, formatter):
        """测试新交易通知格式化"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        change = {
            'type': 'new_transaction',
            'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
            'tx_type': 'transfer',
            'amount': '1.0',
            'block_number': 12345
        }
        
        result = formatter.format_change_notification(address, change)
        
        assert "🔄" in result  # 包含正确的表情符号
        assert "新交易" in result
        assert "转账" in result  # 交易类型
        assert "1.0 ETH" in result  # 金额
        assert "0x1234...45678" in result  # 交易哈希格式化
        assert "#12345" in result  # 区块号
        assert "[查看详情]" in result  # 链接
    
    def test_format_notification(self, formatter):
        """测试通用通知格式化"""
        notification_data = {
            'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6',
            'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
            'tx_type': 'transfer',
            'amount': '1.5',
            'token_symbol': 'ETH',
            'timestamp': '2024-01-01 12:00:00'
        }
        
        result = formatter.format_notification(notification_data)
        
        assert "聪明钱地址有新动态" in result
        assert "0x742d...f0bEb6" in result  # 地址格式化
        assert "转账" in result  # 交易类型
        assert "1.5 ETH" in result  # 金额和代币
        assert "2024-01-01 12:00:00" in result  # 时间戳
        assert "0x1234...45678" in result  # 交易哈希
        assert "[查看详情]" in result  # 链接
    
    def test_format_test_notification(self, formatter):
        """测试通知格式化"""
        notification_data = {
            'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6',
            'is_test': True
        }
        
        result = formatter.format_notification(notification_data)
        
        assert "🧪" in result  # 测试表情符号
        assert "测试通知" in result
        assert "这是一条测试消息" in result
        assert "通知系统正常工作" in result
    
    def test_format_summary_report(self, formatter):
        """测试汇总报告格式化"""
        summary_data = {
            'total_addresses': 50,
            'active_addresses': 30,
            'total_changes': 15,
            'scan_duration': 2.5
        }
        
        result = formatter.format_summary_report(summary_data)
        
        assert "📊" in result  # 汇总表情符号
        assert "监控汇总报告" in result
        assert "总监控地址：50" in result
        assert "活跃地址：30" in result
        assert "检测到变化：15" in result
        assert "变化率：50.0%" in result  # (15/30)*100
        assert "扫描耗时：2.50s" in result
    
    def test_format_error_message(self, formatter):
        """测试错误消息格式化"""
        error_type = "数据库连接失败"
        error_details = "无法连接到SQLite数据库"
        
        result = formatter.format_error_message(error_type, error_details)
        
        assert "⚠️" in result  # 警告表情符号
        assert "系统错误" in result
        assert "数据库连接失败" in result
        assert "无法连接到SQLite数据库" in result
        assert datetime.now().strftime('%Y-%m-%d') in result  # 包含当前日期
    
    def test_format_help_message(self, formatter):
        """测试帮助消息格式化"""
        result = formatter.format_help_message()
        
        assert "📚" in result  # 帮助表情符号
        assert "机器人使用帮助" in result
        assert "核心功能" in result
        assert "常用命令" in result
        assert "/add" in result
        assert "/remove" in result
        assert "/list" in result
        assert "注意事项" in result
    
    def test_format_large_transaction_alert(self, formatter):
        """测试大额交易警报格式化"""
        tx_data = {
            'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6',
            'amount': '15000',
            'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
            'tx_type': 'transfer'
        }
        
        result = formatter.format_large_transaction_alert(tx_data, threshold=10000)
        
        assert "🚨" in result  # 警报表情符号
        assert "大额交易警报" in result
        assert "$15,000.00" in result  # 格式化的大额金额
        assert "0x742d...f0bEb6" in result  # 地址格式化
        assert "0x1234...45678" in result  # 交易哈希格式化
        assert "超过 $10,000" in result  # 阈值信息
    
    def test_format_market_movement_alert(self, formatter):
        """测试市场异动警报格式化"""
        movement_data = {
            'direction': 'up',
            'magnitude': 5.2,
            'affected_addresses': [
                '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6',
                '0x1234567890123456789012345678901234567890',
                '0xAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAb',
                '0x1111111111111111111111111111111111111111',
                '0x2222222222222222222222222222222222222222',
                '0x3333333333333333333333333333333333333333'
            ]
        }
        
        result = formatter.format_market_movement_alert(movement_data)
        
        assert "📈" in result  # 上涨表情符号
        assert "市场异动警报" in result
        assert "方向：up" in result
        assert "幅度：5.20%" in result
        assert "影响地址数：6" in result
        assert "0x742d...f0bEb6" in result  # 第一个地址格式化
        assert "...还有 1 个地址" in result  # 应该显示还有1个（总共6个，显示前5个）
    
    def test_format_address(self, formatter):
        """测试地址格式化"""
        # 测试标准地址
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        result = formatter._format_address(address)
        assert result == "0x742d...f0bEb6"
        
        # 测试短地址
        short_address = "0x123"
        result = formatter._format_address(short_address)
        assert result == "0x123"  # 保持不变
        
        # 测试空地址
        empty_address = ""
        result = formatter._format_address(empty_address)
        assert result == ""
        
        # 测试None
        none_address = None
        result = formatter._format_address(none_address)
        assert result is None
    
    def test_format_tx_hash(self, formatter):
        """测试交易哈希格式化"""
        # 测试标准哈希
        tx_hash = "0x1234567890abcdef1234567890abcdef12345678"
        result = formatter._format_tx_hash(tx_hash)
        assert result == "0x1234...45678"
        
        # 测试短哈希
        short_hash = "0x123"
        result = formatter._format_tx_hash(short_hash)
        assert result == "0x123"  # 保持不变
        
        # 测试空哈希
        empty_hash = ""
        result = formatter._format_tx_hash(empty_hash)
        assert result == ""
    
    def test_get_transaction_description(self, formatter):
        """测试交易类型描述"""
        descriptions = {
            'buy': '买入',
            'sell': '卖出',
            'transfer': '转账',
            'receive': '接收',
            'unknown': '未知交易'
        }
        
        for tx_type, expected_desc in descriptions.items():
            result = formatter._get_transaction_description(tx_type)
            assert result == expected_desc
        
        # 测试未知类型
        result = formatter._get_transaction_description('invalid_type')
        assert result == '未知交易'
    
    def test_truncate_message(self, formatter):
        """测试消息截断"""
        # 创建长消息
        long_message = "这是一个很长的消息。" * 500  # 超过Telegram限制
        
        result = formatter.truncate_message(long_message, max_length=100)
        
        assert len(result) <= 100
        assert "...（内容过长，已截断）" in result
        
        # 测试短消息（不应该被截断）
        short_message = "这是一个短消息。"
        result = formatter.truncate_message(short_message, max_length=100)
        assert result == short_message
        
        # 测试刚好在边界的消息
        boundary_message = "x" * 90
        result = formatter.truncate_message(boundary_message, max_length=100)
        assert result == boundary_message
    
    def test_markdown_formatting(self, formatter):
        """测试Markdown格式"""
        # 确保所有格式化的消息都正确使用Markdown
        change = {
            'type': 'balance_increase',
            'old_balance': '1.0',
            'new_balance': '1.5',
            'change_amount': '0.5'
        }
        
        result = formatter.format_change_notification(
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6", change
        )
        
        # 检查Markdown格式
        assert "**余额增加**" in result  # 粗体
        assert "`0x742d...f0bEb6`" in result  # 代码块（用于地址）
        assert "+0.5 ETH" in result  # 普通文本
    
    def test_special_characters_handling(self, formatter):
        """测试特殊字符处理"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        change = {
            'type': 'new_transaction',
            'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
            'tx_type': 'transfer',
            'amount': '1.0',
            'block_number': 12345
        }
        
        result = formatter.format_change_notification(address, change)
        
        # 确保消息不包含可能导致问题的特殊字符
        assert result is not None
        assert len(result) > 0
        
        # 测试包含特殊字符的地址和标签
        special_change = {
            'type': 'initial_monitor',
            'balance': '1.5',
            'transaction_count': 10
        }
        
        result = formatter.format_change_notification(address, special_change)
        assert result is not None
        assert "初始监控" in result
    
    def test_unicode_handling(self, formatter):
        """测试Unicode字符处理"""
        notification_data = {
            'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6',
            'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
            'tx_type': 'transfer',
            'amount': '1.5',
            'token_symbol': 'ETH',
            'timestamp': '2024-01-01 12:00:00'
        }
        
        result = formatter.format_notification(notification_data)
        
        # 确保Unicode字符正确处理
        assert result is not None
        assert "聪明钱地址有新动态" in result
        assert "🔍" in result  # 表情符号
        assert "💰" in result  # 表情符号
        assert "🔄" in result  # 表情符号
    
    def test_performance_formatting(self, formatter):
        """测试格式化性能"""
        import time
        
        # 创建测试数据
        change = {
            'type': 'balance_increase',
            'old_balance': '1.0',
            'new_balance': '1.5',
            'change_amount': '0.5'
        }
        
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 多次格式化测试性能
        start_time = time.time()
        for _ in range(1000):
            result = formatter.format_change_notification(address, change)
            assert result is not None
        
        duration = time.time() - start_time
        
        # 应该在合理时间内完成（1000次格式化应该小于1秒）
        assert duration < 1.0
        
        # 计算平均每次格式化的耗时
        avg_duration = duration / 1000
        print(f"平均格式化耗时: {avg_duration*1000:.3f}ms")  # 用于性能监控
    
    def test_format_consistency(self, formatter):
        """测试格式化一致性"""
        change = {
            'type': 'new_transaction',
            'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
            'tx_type': 'transfer',
            'amount': '1.0',
            'block_number': 12345
        }
        
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 多次格式化应该产生一致的结果
        results = []
        for _ in range(5):
            result = formatter.format_change_notification(address, change)
            results.append(result)
        
        # 所有结果应该相同
        assert all(result == results[0] for result in results)
    
    def test_edge_case_formatting(self, formatter):
        """测试边界情况格式化"""
        # 测试空数据
        result = formatter.format_change_notification("", {})
        assert result is not None
        
        # 测试None数据
        result = formatter.format_change_notification(None, None)
        assert result is not None
        
        # 测试极小数值
        tiny_change = {
            'type': 'balance_increase',
            'old_balance': '0.000001',
            'new_balance': '0.000001001',
            'change_amount': '0.000000001'
        }
        
        result = formatter.format_change_notification(
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6", tiny_change
        )
        assert result is not None
        assert "0.000001" in result
        
        # 测试极大数值
        huge_change = {
            'type': 'balance_increase',
            'old_balance': '1000000',
            'new_balance': '2000000',
            'change_amount': '1000000'
        }
        
        result = formatter.format_change_notification(
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6", huge_change
        )
        assert result is not None
        assert "1000000" in result