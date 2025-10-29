import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
from web3 import Web3

from config import Config

logger = logging.getLogger(__name__)

class HyperliquidDataFetcher:
    """Hypeliquid数据获取器 - 负责从链上获取数据"""
    
    def __init__(self):
        self.session = None
        self.rate_limiter = RateLimiter(Config.API_RATE_LIMIT)
        self.w3 = Web3(Web3.HTTPProvider(Config.HYPERLIQUID_EVM_RPC))
        
        # API端点
        self.l1_api_base = Config.HYPERLIQUID_API_BASE
        self.evm_rpc_url = Config.HYPERLIQUID_EVM_RPC
    
    async def __aenter__(self):
        """异步上下文管理器进入"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
            headers={'User-Agent': 'HypeliquidSmartMoneyBot/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
    
    async def get_address_state(self, address: str) -> Optional[Dict[str, Any]]:
        """
        获取地址的完整状态
        包括余额、交易数、最新交易等
        """
        try:
            # 等待速率限制
            await self.rate_limiter.wait()
            
            # 并行获取不同类型的数据
            tasks = [
                self._get_evm_balance(address),
                self._get_transaction_count(address),
                self._get_latest_transaction(address),
                self._get_user_state(address)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            balance = results[0] if not isinstance(results[0], Exception) else "0"
            tx_count = results[1] if not isinstance(results[1], Exception) else 0
            latest_tx = results[2] if not isinstance(results[2], Exception) else None
            user_state = results[3] if not isinstance(results[3], Exception) else None
            
            # 构建状态数据
            state_data = {
                'address': address.lower(),
                'balance': str(balance),
                'transaction_count': tx_count,
                'last_tx_hash': latest_tx.get('hash') if latest_tx else None,
                'last_tx_time': latest_tx.get('timestamp') if latest_tx else None,
                'last_block_number': latest_tx.get('blockNumber') if latest_tx else None,
                'evm_data': {
                    'balance': balance,
                    'transaction_count': tx_count
                },
                'latest_transaction': latest_tx,
                'user_state': user_state,
                'scan_time': datetime.now().isoformat()
            }
            
            return state_data
            
        except Exception as e:
            logger.error(f"获取地址状态失败 {address}: {e}")
            return None
    
    async def _get_evm_balance(self, address: str) -> str:
        """获取EVM余额"""
        try:
            # 使用Web3获取余额
            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = self.w3.from_wei(balance_wei, 'ether')
            return str(balance_eth)
        except Exception as e:
            logger.error(f"获取EVM余额失败 {address}: {e}")
            return "0"
    
    async def _get_transaction_count(self, address: str) -> int:
        """获取交易数量"""
        try:
            # 使用Web3获取交易数量
            tx_count = self.w3.eth.get_transaction_count(address)
            return tx_count
        except Exception as e:
            logger.error(f"获取交易数量失败 {address}: {e}")
            return 0
    
    async def _get_latest_transaction(self, address: str) -> Optional[Dict]:
        """获取最新交易"""
        try:
            # 通过RPC获取最新交易
            # 注意：标准的eth_getTransactionCount不会返回交易详情
            # 这里我们需要通过其他方式获取
            
            # 获取最新的区块
            latest_block = self.w3.eth.get_block('latest', full_transactions=True)
            
            # 在当前区块中查找相关交易
            for tx in latest_block.transactions:
                if (tx.get('from', '').lower() == address.lower() or 
                    tx.get('to', '').lower() == address.lower()):
                    return {
                        'hash': tx['hash'].hex(),
                        'from': tx['from'],
                        'to': tx.get('to'),
                        'value': str(self.w3.from_wei(tx['value'], 'ether')),
                        'gas': tx['gas'],
                        'gasPrice': str(tx['gasPrice']),
                        'blockNumber': tx['blockNumber'],
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"获取最新交易失败 {address}: {e}")
            return None
    
    async def _get_user_state(self, address: str) -> Optional[Dict]:
        """通过Hyperliquid L1 API获取用户状态"""
        try:
            url = f"{self.l1_api_base}/info"
            payload = {
                "type": "userState",
                "user": address
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"L1 API返回错误状态: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取用户状态失败 {address}: {e}")
            return None
    
    async def get_recent_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """获取地址的最近交易"""
        try:
            # 等待速率限制
            await self.rate_limiter.wait()
            
            # 获取最新的几个区块
            latest_block_number = self.w3.eth.block_number
            transactions = []
            
            # 扫描最近的10个区块
            for block_num in range(latest_block_number, max(latest_block_number - 10, 0), -1):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        if (tx.get('from', '').lower() == address.lower() or 
                            tx.get('to', '').lower() == address.lower()):
                            
                            tx_data = {
                                'hash': tx['hash'].hex(),
                                'from': tx['from'],
                                'to': tx.get('to'),
                                'value': str(self.w3.from_wei(tx['value'], 'ether')),
                                'gas': tx['gas'],
                                'gasPrice': str(tx['gasPrice']),
                                'blockNumber': tx['blockNumber'],
                                'timestamp': datetime.now().isoformat(),
                                'type': self._classify_transaction(tx, address)
                            }
                            
                            transactions.append(tx_data)
                            
                            if len(transactions) >= limit:
                                return transactions
                                
                except Exception as e:
                    logger.warning(f"获取区块 {block_num} 失败: {e}")
                    continue
            
            return transactions
            
        except Exception as e:
            logger.error(f"获取最近交易失败 {address}: {e}")
            return []
    
    def _classify_transaction(self, tx: Dict, monitored_address: str) -> str:
        """分类交易类型"""
        from_addr = tx.get('from', '').lower()
        to_addr = tx.get('to', '').lower() if tx.get('to') else None
        monitored_addr = monitored_address.lower()
        
        if from_addr == monitored_addr and to_addr:
            return 'transfer'  # 转出
        elif to_addr == monitored_addr:
            return 'receive'   # 接收
        else:
            return 'unknown'
    
    async def get_user_fills(self, address: str, start_time: Optional[int] = None) -> List[Dict]:
        """获取用户的交易成交记录"""
        try:
            # 等待速率限制
            await self.rate_limiter.wait()
            
            url = f"{self.l1_api_base}/info"
            payload = {
                "type": "userFills",
                "user": address
            }
            
            if start_time:
                payload["startTime"] = start_time
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.warning(f"获取用户成交记录失败: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"获取用户成交记录失败 {address}: {e}")
            return []
    
    async def detect_address_changes(self, address: str, old_state: Optional[Dict], 
                                   new_state: Dict) -> List[Dict]:
        """
        检测地址状态变化
        返回变化列表，每个变化包含类型和详细信息
        """
        changes = []
        
        try:
            if not old_state:
                # 首次监控，记录初始状态
                changes.append({
                    'type': 'initial_monitor',
                    'address': address,
                    'balance': new_state.get('balance', '0'),
                    'transaction_count': new_state.get('transaction_count', 0),
                    'message': f'开始监控地址 {address}'
                })
                return changes
            
            # 检查余额变化
            old_balance = float(old_state.get('balance', '0'))
            new_balance = float(new_state.get('balance', '0'))
            
            if old_balance != new_balance:
                balance_change = new_balance - old_balance
                change_type = 'balance_increase' if balance_change > 0 else 'balance_decrease'
                
                changes.append({
                    'type': change_type,
                    'address': address,
                    'old_balance': str(old_balance),
                    'new_balance': str(new_balance),
                    'change_amount': str(abs(balance_change)),
                    'message': f'余额变化: {old_balance:.4f} → {new_balance:.4f} ETH'
                })
            
            # 检查新交易
            old_tx_count = old_state.get('transaction_count', 0)
            new_tx_count = new_state.get('transaction_count', 0)
            
            if new_tx_count > old_tx_count:
                # 获取新交易详情
                new_transactions = await self.get_new_transactions(
                    address, 
                    old_state.get('last_tx_hash'),
                    new_state.get('last_tx_hash')
                )
                
                for tx in new_transactions:
                    changes.append({
                        'type': 'new_transaction',
                        'address': address,
                        'tx_hash': tx['hash'],
                        'tx_type': tx.get('type', 'unknown'),
                        'amount': tx.get('value', '0'),
                        'from': tx.get('from'),
                        'to': tx.get('to'),
                        'block_number': tx.get('blockNumber'),
                        'message': f'新交易: {tx.get("type", "unknown")} {tx.get("value", "0")} ETH'
                    })
            
            return changes
            
        except Exception as e:
            logger.error(f"检测地址变化失败 {address}: {e}")
            return []
    
    async def get_new_transactions(self, address: str, old_last_tx: Optional[str], 
                                  new_last_tx: Optional[str]) -> List[Dict]:
        """获取新交易（在两个交易哈希之间）"""
        try:
            if not new_last_tx:
                return []
            
            # 获取最近的交易
            recent_txs = await self.get_recent_transactions(address, limit=20)
            
            new_transactions = []
            found_old_tx = False
            
            for tx in recent_txs:
                if old_last_tx and tx['hash'] == old_last_tx:
                    found_old_tx = True
                    break
                
                new_transactions.append(tx)
            
            # 如果没找到旧交易，限制返回数量避免过多数据
            if not found_old_tx:
                return new_transactions[:5]  # 最多返回5条
            
            return new_transactions
            
        except Exception as e:
            logger.error(f"获取新交易失败 {address}: {e}")
            return []
    
    async def get_token_balance(self, address: str, token_address: str) -> str:
        """获取特定代币余额"""
        try:
            # 简单的ERC20余额查询
            # 这里需要代币合约的ABI，简化处理
            return "0"  # 暂时返回0，后续可以扩展
        except Exception as e:
            logger.error(f"获取代币余额失败 {address} {token_address}: {e}")
            return "0"


class RateLimiter:
    """速率限制器 - 控制API请求频率"""
    
    def __init__(self, max_requests_per_second: float):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = asyncio.Lock()
    
    async def wait(self):
        """等待直到可以发送下一个请求"""
        async with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                await asyncio.sleep(wait_time)
            
            self.last_request_time = time.time()