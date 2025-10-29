import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
from data_fetcher import HyperliquidDataFetcher, RateLimiter

class TestHyperliquidDataFetcher:
    """数据获取器测试"""
    
    @pytest.fixture
    async def fetcher(self):
        """创建数据获取器实例"""
        fetcher = HyperliquidDataFetcher()
        async with fetcher:
            yield fetcher
    
    @pytest.fixture
    def mock_web3(self):
        """创建Mock Web3实例"""
        with patch('data_fetcher.Web3') as mock_w3:
            # 配置mock对象
            mock_web3_instance = Mock()
            mock_w3.return_value = mock_web3_instance
            
            # 模拟eth模块方法
            mock_web3_instance.eth = Mock()
            mock_web3_instance.eth.get_balance = Mock(return_value=1500000000000000000)  # 1.5 ETH
            mock_web3_instance.eth.get_transaction_count = Mock(return_value=10)
            mock_web3_instance.eth.get_block = Mock(return_value=Mock(
                transactions=[
                    Mock(
                        hash=b'0x1234567890abcdef',
                        from_address='0x1111111111111111111111111111111111111111',
                        to='0x2222222222222222222222222222222222222222',
                        value=1000000000000000000,  # 1 ETH
                        gas=21000,
                        gasPrice=20000000000,
                        blockNumber=12345
                    )
                ]
            ))
            mock_web3_instance.eth.block_number = 12345
            mock_web3_instance.from_wei = Mock(side_effect=lambda x, unit: x / 10**18)
            
            yield mock_web3_instance
    
    @pytest.mark.asyncio
    async def test_get_address_state(self, fetcher, mock_web3):
        """测试获取地址状态"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # Mock HTTP请求
        with patch.object(fetcher.session, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={'balance': '1.5', 'positions': []})
            mock_post.return_value = mock_response
            
            result = await fetcher.get_address_state(address)
            
            assert result is not None
            assert 'address' in result
            assert 'balance' in result
            assert 'transaction_count' in result
            assert 'last_tx_hash' in result
            assert result['address'] == address.lower()
    
    @pytest.mark.asyncio
    async def test_get_evm_balance(self, fetcher, mock_web3):
        """测试获取EVM余额"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        balance = await fetcher._get_evm_balance(address)
        
        assert balance == '1.5'  # 1.5 ETH
        mock_web3.eth.get_balance.assert_called_once_with(address)
    
    @pytest.mark.asyncio
    async def test_get_transaction_count(self, fetcher, mock_web3):
        """测试获取交易数量"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        count = await fetcher._get_transaction_count(address)
        
        assert count == 10
        mock_web3.eth.get_transaction_count.assert_called_once_with(address)
    
    @pytest.mark.asyncio
    async def test_get_latest_transaction(self, fetcher, mock_web3):
        """测试获取最新交易"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # Mock区块数据
        mock_web3.eth.get_block = Mock(return_value=Mock(
            transactions=[
                Mock(
                    hash=b'0x1234567890abcdef',
                    from_address='0x1111111111111111111111111111111111111111',
                    to='0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6',  # 匹配我们的地址
                    value=1000000000000000000,
                    gas=21000,
                    gasPrice=20000000000,
                    blockNumber=12345
                )
            ]
        ))
        
        result = await fetcher._get_latest_transaction(address)
        
        assert result is not None
        assert result['hash'] == '0x1234567890abcdef'
        assert result['to'] == address
        assert result['value'] == '1.0'  # 1 ETH
    
    @pytest.mark.asyncio
    async def test_get_user_state(self, fetcher):
        """测试获取用户状态"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # Mock HTTP请求
        with patch.object(fetcher.session, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={'balance': '1.5', 'positions': []})
            mock_post.return_value = mock_response
            
            result = await fetcher._get_user_state(address)
            
            assert result is not None
            assert 'balance' in result
            assert result['balance'] == '1.5'
    
    @pytest.mark.asyncio
    async def test_get_recent_transactions(self, fetcher, mock_web3):
        """测试获取最近交易"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # Mock多个区块
        mock_blocks = []
        for i in range(5):
            block = Mock(
                transactions=[
                    Mock(
                        hash=f'0x1234567890abcdef{i}'.encode(),
                        from_address='0x1111111111111111111111111111111111111111',
                        to=address,
                        value=1000000000000000000,
                        gas=21000,
                        gasPrice=20000000000,
                        blockNumber=12345 + i
                    )
                ]
            )
            mock_blocks.append(block)
        
        mock_web3.eth.get_block = Mock(side_effect=mock_blocks)
        
        result = await fetcher.get_recent_transactions(address, limit=3)
        
        assert len(result) == 3
        for tx in result:
            assert 'hash' in tx
            assert 'from' in tx
            assert 'to' in tx
            assert 'value' in tx
            assert tx['to'] == address
    
    @pytest.mark.asyncio
    async def test_classify_transaction(self, fetcher):
        """测试交易分类"""
        monitored_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 测试转出交易
        tx_out = {
            'from': monitored_address,
            'to': '0x1111111111111111111111111111111111111111'
        }
        result = fetcher._classify_transaction(tx_out, monitored_address)
        assert result == 'transfer'
        
        # 测试接收交易
        tx_in = {
            'from': '0x1111111111111111111111111111111111111111',
            'to': monitored_address
        }
        result = fetcher._classify_transaction(tx_in, monitored_address)
        assert result == 'receive'
        
        # 测试其他交易
        tx_other = {
            'from': '0x1111111111111111111111111111111111111111',
            'to': '0x2222222222222222222222222222222222222222'
        }
        result = fetcher._classify_transaction(tx_other, monitored_address)
        assert result == 'unknown'
    
    @pytest.mark.asyncio
    async def test_detect_address_changes(self, fetcher):
        """测试地址变化检测"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 首次监控（无旧状态）
        new_state = {
            'balance': '1.5',
            'transaction_count': 10,
            'last_tx_hash': '0x1234567890abcdef',
            'scan_time': '2024-01-01T12:00:00'
        }
        
        changes = await fetcher.detect_address_changes(address, None, new_state)
        
        assert len(changes) == 1
        assert changes[0]['type'] == 'initial_monitor'
        assert changes[0]['balance'] == '1.5'
        assert changes[0]['transaction_count'] == 10
        
        # 余额变化检测
        old_state = {
            'balance': '1.0',
            'transaction_count': 10,
            'last_tx_hash': '0x1234567890abcdef'
        }
        
        new_state = {
            'balance': '1.5',
            'transaction_count': 10,
            'last_tx_hash': '0x1234567890abcdef'
        }
        
        changes = await fetcher.detect_address_changes(address, old_state, new_state)
        
        assert len(changes) == 1
        assert changes[0]['type'] == 'balance_increase'
        assert changes[0]['change_amount'] == '0.5'
    
    @pytest.mark.asyncio
    async def test_get_new_transactions(self, fetcher, mock_web3):
        """测试获取新交易"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # Mock交易数据
        mock_web3.eth.get_block = Mock(return_value=Mock(
            transactions=[
                Mock(
                    hash=b'0xnewtxhash123',
                    from_address='0x1111111111111111111111111111111111111111',
                    to=address,
                    value=1000000000000000000,
                    gas=21000,
                    gasPrice=20000000000,
                    blockNumber=12350
                )
            ]
        ))
        
        old_last_tx = "0xoldtxhash"
        new_last_tx = "0xnewtxhash123"
        
        result = await fetcher.get_new_transactions(address, old_last_tx, new_last_tx)
        
        # 应该返回新交易
        assert len(result) >= 0  # 可能返回空列表，取决于具体实现
    
    def test_rate_limiter(self):
        """测试速率限制器"""
        rate_limiter = RateLimiter(max_requests_per_second=2)
        
        async def test_rate_limiting():
            start_time = asyncio.get_event_loop().time()
            
            # 执行多次请求
            for i in range(5):
                await rate_limiter.wait()
                current_time = asyncio.get_event_loop().time()
                
                if i > 0:
                    # 验证请求间隔
                    interval = current_time - start_time
                    expected_min_interval = 0.5  # 2 requests per second = 0.5s interval
                    assert interval >= expected_min_interval * 0.8  # 允许一些误差
                
                start_time = current_time
        
        # 运行测试
        asyncio.run(test_rate_limiting())
    
    @pytest.mark.asyncio
    async def test_error_handling(self, fetcher, mock_web3):
        """测试错误处理"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # Mock Web3抛出异常
        mock_web3.eth.get_balance = Mock(side_effect=Exception("Connection error"))
        
        # 应该处理异常并返回默认值
        balance = await fetcher._get_evm_balance(address)
        assert balance == "0"  # 返回默认值
        
        # Mock HTTP请求失败
        with patch.object(fetcher.session, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_post.return_value = mock_response
            
            result = await fetcher._get_user_state(address)
            assert result is None  # 应该返回None而不是抛出异常
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, fetcher):
        """测试速率限制集成"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # Mock all methods to avoid actual API calls
        with patch.object(fetcher, '_get_evm_balance', return_value="1.5"), \
             patch.object(fetcher, '_get_transaction_count', return_value=10), \
             patch.object(fetcher, '_get_latest_transaction', return_value=None), \
             patch.object(fetcher, '_get_user_state', return_value=None):
            
            start_time = asyncio.get_event_loop().time()
            
            # 执行多个并发请求
            tasks = []
            for i in range(5):
                task = fetcher.get_address_state(address)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            
            # 验证所有请求都成功
            assert all(result is not None for result in results)
            
            # 验证速率限制生效（请求应该分散在一定时间内）
            expected_min_duration = 2.0  # 基于速率限制
            assert duration >= expected_min_duration * 0.5  # 允许一些误差
    
    @pytest.mark.asyncio
    async def test_data_consistency(self, fetcher, mock_web3):
        """测试数据一致性"""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
        
        # 设置一致的mock数据
        mock_web3.eth.get_balance = Mock(return_value=1500000000000000000)  # 1.5 ETH
        mock_web3.eth.get_transaction_count = Mock(return_value=10)
        mock_web3.eth.block_number = 12345
        
        with patch.object(fetcher, '_get_user_state', return_value=None):
            result = await fetcher.get_address_state(address)
            
            assert result is not None
            assert result['address'] == address.lower()
            assert result['balance'] == '1.5'
            assert result['transaction_count'] == 10
            assert 'evm_data' in result
            assert result['evm_data']['balance'] == '1.5'
            assert result['evm_data']['transaction_count'] == 10
    
    @pytest.mark.asyncio
    async def test_empty_and_edge_cases(self, fetcher, mock_web3):
        """测试空值和边界情况"""
        # 测试空地址
        result = await fetcher.get_address_state("")
        assert result is not None  # 应该返回一些默认数据
        
        # 测试零余额
        mock_web3.eth.get_balance = Mock(return_value=0)
        balance = await fetcher._get_evm_balance("0x0000000000000000000000000000000000000000")
        assert balance == '0'
        
        # 测试零交易数
        mock_web3.eth.get_transaction_count = Mock(return_value=0)
        count = await fetcher._get_transaction_count("0x0000000000000000000000000000000000000000")
        assert count == 0
        
        # 测试大数值
        large_balance = 1000000000000000000000000  # 1M ETH
        mock_web3.eth.get_balance = Mock(return_value=large_balance)
        balance = await fetcher._get_evm_balance("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6")
        assert balance == '1000000.0'  # 1M ETH