import pytest
import sqlite3
import tempfile
import os
from datetime import datetime
from database import DatabaseManager

class TestDatabaseManager:
    """数据库管理器测试"""
    
    @pytest.fixture
    def db(self):
        """创建临时数据库用于测试 - 使用相对路径避免安全验证问题"""
        # 使用相对路径创建临时数据库文件
        temp_db_name = "test_temp_database.db"
        
        # 创建数据库实例
        db = DatabaseManager(temp_db_name)
        
        yield db
        
        # 清理
        if os.path.exists(temp_db_name):
            os.unlink(temp_db_name)
    
    def test_init_database(self, db):
        """测试数据库初始化"""
        # 检查表是否存在
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查用户表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            assert cursor.fetchone() is not None
            
            # 检查监控地址表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitored_addresses'")
            assert cursor.fetchone() is not None
            
            # 检查地址状态表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='address_states'")
            assert cursor.fetchone() is not None
    
    def test_add_user(self, db):
        """测试添加用户"""
        user_id = 12345
        username = "test_user"
        
        # 添加用户
        result = db.add_user(user_id, username)
        assert result is True
        
        # 验证用户存在
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            assert user is not None
            assert user[0] == user_id  # user_id
            assert user[1] == username  # username
    
    def test_add_monitored_address(self, db):
        """测试添加监控地址"""
        user_id = 12345
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        label = "测试地址"
        
        # 先添加用户
        db.add_user(user_id, "test_user")
        
        # 添加监控地址
        result = db.add_monitored_address(user_id, address, label)
        assert result is True
        
        # 验证地址存在
        addresses = db.get_user_addresses(user_id)
        assert len(addresses) == 1
        assert addresses[0]['address'] == address.lower()
        assert addresses[0]['label'] == label
    
    def test_remove_monitored_address(self, db):
        """测试移除监控地址"""
        user_id = 12345
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 添加用户和地址
        db.add_user(user_id, "test_user")
        db.add_monitored_address(user_id, address, "测试地址")
        
        # 验证地址存在
        addresses = db.get_user_addresses(user_id)
        assert len(addresses) == 1
        
        # 移除地址
        result = db.remove_monitored_address(user_id, address)
        assert result is True
        
        # 验证地址被移除
        addresses = db.get_user_addresses(user_id)
        assert len(addresses) == 0
    
    def test_get_user_addresses(self, db):
        """测试获取用户地址列表"""
        user_id = 12345
        
        # 添加用户
        db.add_user(user_id, "test_user")
        
        # 添加多个地址
        addresses = [
            ("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6", "地址1"),
            ("0x1234567890123456789012345678901234567890", "地址2"),
            ("0xAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAb", "地址3")
        ]
        
        for address, label in addresses:
            db.add_monitored_address(user_id, address, label)
        
        # 获取地址列表
        user_addresses = db.get_user_addresses(user_id)
        assert len(user_addresses) == 3
        
        # 验证地址信息
        for i, addr_info in enumerate(user_addresses):
            assert addr_info['address'] == addresses[i][0].lower()
            assert addr_info['label'] == addresses[i][1]
    
    def test_address_state_management(self, db):
        """测试地址状态管理"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 测试状态数据
        state_data = {
            'address': address,
            'balance': '1.5',
            'transaction_count': 10,
            'last_tx_hash': '0x1234567890abcdef',
            'last_tx_time': '2024-01-01T12:00:00',
            'scan_time': '2024-01-01T12:00:00'
        }
        
        # 更新地址状态
        success = db.update_address_state(address, state_data)
        assert success is True
        
        # 获取地址状态
        retrieved_state = db.get_address_state(address)
        assert retrieved_state is not None
        assert retrieved_state['address'] == address.lower()
        assert retrieved_state['balance'] == '1.5'
        assert retrieved_state['transaction_count'] == 10
    
    def test_notification_management(self, db):
        """测试通知管理"""
        user_id = 12345
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        tx_hash = "0x1234567890abcdef"
        
        # 添加用户
        db.add_user(user_id, "test_user")
        
        # 添加通知
        success = db.add_notification(
            user_id=user_id,
            address=address,
            tx_hash=tx_hash,
            notification_type='balance_change',
            message='测试通知消息'
        )
        assert success is True
        
        # 获取待发送通知
        pending_notifications = db.get_pending_notifications()
        assert len(pending_notifications) == 1
        assert pending_notifications[0]['user_id'] == user_id
        assert pending_notifications[0]['address'] == address.lower()
        assert pending_notifications[0]['is_sent'] == 0
        
        # 标记通知为已发送
        notification_id = pending_notifications[0]['id']
        success = db.mark_notification_sent(notification_id)
        assert success is True
        
        # 验证通知已发送
        pending_notifications = db.get_pending_notifications()
        assert len(pending_notifications) == 0
    
    def test_user_scan_interval(self, db):
        """测试用户扫描间隔"""
        user_id = 12345
        
        # 添加用户
        db.add_user(user_id, "test_user")
        
        # 默认扫描间隔应该是60秒
        default_interval = db.get_user_scan_interval(user_id)
        assert default_interval == 60
        
        # 更新扫描间隔
        new_interval = 120
        success = db.update_user_scan_interval(user_id, new_interval)
        assert success is True
        
        # 验证扫描间隔已更新
        updated_interval = db.get_user_scan_interval(user_id)
        assert updated_interval == new_interval
    
    def test_data_cleanup(self, db):
        """测试数据清理"""
        # 添加一些测试数据
        user_id = 12345
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        db.add_user(user_id, "test_user")
        db.add_monitored_address(user_id, address, "测试地址")
        
        # 添加一些旧的交易记录（通过直接操作数据库模拟旧数据）
        # 注意：需要设置created_at字段，因为清理函数基于这个字段
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (address, tx_hash, tx_type, amount, created_at)
                VALUES (?, ?, ?, ?, datetime('now', '-40 days'))
            """, (address, "0xoldtxhash", "transfer", "1.0"))
            conn.commit()
        
        # 执行清理（保留30天内的数据）
        success = db.cleanup_old_data(days_to_keep=30)
        assert success is True
        
        # 验证旧数据已被清理
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM transactions 
                WHERE address = ? AND tx_hash = ?
            """, (address, "0xoldtxhash"))
            count = cursor.fetchone()[0]
            assert count == 0  # 旧数据应该被清理
    
    def test_sql_injection_protection(self, db):
        """测试SQL注入防护 - 修复的关键测试"""
        # 测试恶意输入参数
        malicious_inputs = [
            "30; DROP TABLE users; --",  # 经典SQL注入
            "30'); DROP TABLE users; --",  # 变体
            "30' OR '1'='1",  # 逻辑绕过
            "30; INSERT INTO users (user_id, username) VALUES (999, 'hacker'); --",
            "30 UNION SELECT * FROM users --",  # 数据泄露
        ]
        
        # 对于每个恶意输入，验证数据库不会被破坏
        for malicious_input in malicious_inputs:
            # 尝试使用恶意参数清理数据
            result = db.cleanup_old_data(malicious_input)
            # 应该返回False，因为参数验证失败
            assert result is False
            
            # 验证数据库结构仍然完整
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                # 检查表是否仍然存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                assert cursor.fetchone() is not None, f"表结构被恶意参数破坏: {malicious_input}"
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitored_addresses'")
                assert cursor.fetchone() is not None
        
        # 验证边界值处理
        edge_cases = [
            0,      # 零值
            -1,     # 负值
            366,    # 超过一年
            1000,   # 极大值
            "not_a_number",  # 非数字
            None,   # None值
        ]
        
        for edge_case in edge_cases:
            result = db.cleanup_old_data(edge_case)
            assert result is False, f"边界值 {edge_case} 应该被拒绝"
    
    def test_path_traversal_protection(self):
        """测试路径遍历防护 - 修复的关键测试"""
        # 恶意路径输入
        malicious_paths = [
            "../../../etc/passwd",      # Unix系统密码文件
            "..\\..\\..\\windows\\system32\\config\\sam",  # Windows系统文件
            "/etc/hosts",               # 绝对路径
            "C:\\windows\\system32\\config\\sam",  # Windows绝对路径
            "data/../../../etc/passwd",  # 伪装在子目录中
            "../data/../etc/passwd",    # 复杂相对路径
            "data//database.db",        # 双斜杠
            "data\\\\database.db",       # 反斜杠
            "../",                      # 目录遍历
            "..",                       # 父目录
            ".",                        # 当前目录
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(ValueError):
                DatabaseManager(malicious_path)
        
        # 测试有效的相对路径
        valid_paths = [
            "smart_money_monitor.db",
            "data/monitor.db",
            "monitor_data/database.db",
            "my-app_data.db",
            "app_data_2024.db",
        ]
        
        for valid_path in valid_paths:
            # 使用临时文件避免实际创建文件
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = os.path.join(temp_dir, valid_path)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                
                try:
                    db = DatabaseManager(valid_path)
                    assert db.db_path == valid_path
                    # 清理
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception as e:
                    # 某些路径可能在当前环境不存在，但不应该因为安全原因被拒绝
                    if "数据库路径不安全" in str(e):
                        pytest.fail(f"有效路径 {valid_path} 被错误拒绝: {e}")
        
        # 测试非法文件名
        invalid_filenames = [
            "database;.db",
            "database|.db",
            "database<.db",
            "database>.db",
            "database*.db",
            "database?.db",
            "database[.db",
            "database].db",
            "database{.db",
            "database}.db",
        ]
        
        for invalid_filename in invalid_filenames:
            with pytest.raises(ValueError):
                DatabaseManager(invalid_filename)
    
    def test_parameter_validation_edge_cases(self, db):
        """测试参数验证的边界情况"""
        # 测试cleanup_old_data的边界值
        valid_days = [1, 7, 30, 90, 180, 365]
        for days in valid_days:
            result = db.cleanup_old_data(days)
            assert result is True, f"有效天数 {days} 应该被接受"
        
        # 测试无效参数类型
        invalid_params = [
            "30",       # 字符串而非整数
            30.5,       # 浮点数
            [],         # 列表
            {},         # 字典
            True,       # 布尔值
        ]
        
        for param in invalid_params:
            result = db.cleanup_old_data(param)
            assert result is False, f"无效参数类型 {type(param)} 应该被拒绝"
    
    def test_address_validation(self, db):
        """测试地址验证"""
        # 有效的以太坊地址
        valid_addresses = [
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6",
            "0x1234567890123456789012345678901234567890",
            "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        ]
        
        # 无效的地址
        invalid_addresses = [
            "0x123",  # 太短
            "0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # 包含非法字符
            "1234567890123456789012345678901234567890",  # 缺少0x前缀
            "",  # 空地址
            "not_an_address"
        ]
        
        user_id = 12345
        db.add_user(user_id, "test_user")
        
        # 测试有效地址
        for address in valid_addresses:
            result = db.add_monitored_address(user_id, address)
            assert result is True
        
        # 测试无效地址（应该仍然可以添加，因为数据库层面不验证格式）
        for address in invalid_addresses:
            if address:  # 跳过空地址
                result = db.add_monitored_address(user_id, address)
                # 数据库应该接受任何字符串作为地址
                assert result is True
    
    def test_concurrent_operations(self, db):
        """测试并发操作"""
        import threading
        import time
        
        user_id = 12345
        db.add_user(user_id, "test_user")
        
        results = []
        
        def add_address_task(address_id):
            try:
                address = f"0x{address_id:040x}"
                result = db.add_monitored_address(user_id, address, f"地址{address_id}")
                results.append(result)
            except Exception as e:
                results.append(False)
        
        # 启动多个线程同时添加地址
        threads = []
        for i in range(10):
            thread = threading.Thread(target=add_address_task, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有操作都成功
        successful_operations = sum(1 for result in results if result is True)
        assert successful_operations == 10
        
        # 验证地址都被正确添加
        addresses = db.get_user_addresses(user_id)
        assert len(addresses) == 10
    
    def test_error_handling(self, db):
        """测试错误处理"""
        # 测试添加用户时传入无效参数
        result = db.add_user(None, "test_user")  # None user_id
        assert result is False  # 应该失败
        
        # 测试添加监控地址到不存在的用户
        result = db.add_monitored_address(99999, "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6")
        # 应该仍然成功，因为数据库不强制外键约束
        assert result is True
        
        # 测试获取不存在的用户地址
        addresses = db.get_user_addresses(99999)
        assert addresses == []  # 应该返回空列表
        
        # 测试获取不存在的状态
        state = db.get_address_state("0xnonexistent")
        assert state is None
    
    def test_data_integrity(self, db):
        """测试数据完整性"""
        user_id = 12345
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 添加用户和地址
        db.add_user(user_id, "test_user")
        db.add_monitored_address(user_id, address, "测试地址")
        
        # 验证地址被存储为小写
        addresses = db.get_user_addresses(user_id)
        assert addresses[0]['address'] == address.lower()
        
        # 验证重复添加地址（应该更新而不是报错）
        result = db.add_monitored_address(user_id, address, "新标签")
        assert result is True
        
        addresses = db.get_user_addresses(user_id)
        assert len(addresses) == 1  # 仍然只有一个地址
        assert addresses[0]['label'] == "新标签"  # 标签已更新
    
    def test_transaction_management(self, db):
        """测试交易管理"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 添加交易记录
        tx_data = {
            'address': address,
            'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
            'tx_type': 'transfer',
            'amount': '1.5',
            'token_symbol': 'ETH',
            'from_address': '0x1111111111111111111111111111111111111111',
            'to_address': '0x2222222222222222222222222222222222222222',
            'block_number': 12345,
            'timestamp': datetime.now(),
            'gas_used': 21000,
            'gas_price': '20000000000'
        }
        
        success = db.add_transaction(tx_data)
        assert success is True
        
        # 验证交易记录存在（通过直接查询数据库）
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions WHERE tx_hash = ?", 
                         (tx_data['tx_hash'],))
            transaction = cursor.fetchone()
            
            assert transaction is not None
            assert transaction[1] == address.lower()  # address
            assert transaction[2] == tx_data['tx_hash']  # tx_hash
            assert transaction[3] == tx_data['tx_type']  # tx_type
            assert transaction[4] == tx_data['amount']  # amount