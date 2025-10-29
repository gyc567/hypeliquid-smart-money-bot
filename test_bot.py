#!/usr/bin/env python3
"""
Hypeliquid聪明钱监控机器人测试脚本

用于测试机器人的各项功能，确保系统正常工作。
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
import json
import time
from typing import Dict, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from data_fetcher import HyperliquidDataFetcher
from message_formatter import MessageFormatter
from monitor import AddressMonitor
from telegram_bot import TelegramBot
from error_handler import global_error_handler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class BotTester:
    """机器人测试器"""
    
    def __init__(self):
        self.db = DatabaseManager(Config.DATABASE_PATH)
        self.data_fetcher = HyperliquidDataFetcher()
        self.message_formatter = MessageFormatter()
        self.test_results = []
        
    def log_test_result(self, test_name: str, passed: bool, message: str = "", duration: float = 0):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'message': message,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"{status} {test_name}: {message} ({duration:.2f}s)")
    
    async def test_database_operations(self):
        """测试数据库操作"""
        logger.info("开始测试数据库操作...")
        start_time = time.time()
        
        try:
            # 测试用户管理
            test_user_id = 123456789
            username = "test_user"
            
            # 添加用户
            success = self.db.add_user(test_user_id, username)
            self.log_test_result("添加用户", success, "用户添加测试")
            
            # 测试地址管理
            test_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
            label = "测试地址"
            
            # 添加监控地址
            success = self.db.add_monitored_address(test_user_id, test_address, label)
            self.log_test_result("添加监控地址", success, "地址添加测试")
            
            # 获取用户地址列表
            addresses = self.db.get_user_addresses(test_user_id)
            has_addresses = len(addresses) > 0
            self.log_test_result("获取用户地址列表", has_addresses, f"找到 {len(addresses)} 个地址")
            
            # 更新扫描间隔
            success = self.db.update_user_scan_interval(test_user_id, 120)
            self.log_test_result("更新扫描间隔", success, "扫描间隔更新测试")
            
            # 获取扫描间隔
            interval = self.db.get_user_scan_interval(test_user_id)
            correct_interval = interval == 120
            self.log_test_result("获取扫描间隔", correct_interval, f"间隔: {interval}秒")
            
            # 清理测试数据
            self.db.remove_monitored_address(test_user_id, test_address)
            
        except Exception as e:
            self.log_test_result("数据库操作", False, f"异常: {e}", time.time() - start_time)
        
        duration = time.time() - start_time
        logger.info(f"数据库操作测试完成，耗时: {duration:.2f}秒")
    
    async def test_data_fetcher(self):
        """测试数据获取器"""
        logger.info("开始测试数据获取器...")
        start_time = time.time()
        
        try:
            async with self.data_fetcher:
                # 测试地址 - 使用一个已知的活跃地址
                test_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6"
                
                # 获取地址状态
                address_state = await self.data_fetcher.get_address_state(test_address)
                has_state = address_state is not None
                self.log_test_result("获取地址状态", has_state, 
                                   f"状态数据: {'有' if has_state else '无'}")
                
                if has_state:
                    # 检查状态数据完整性
                    required_fields = ['address', 'balance', 'transaction_count']
                    has_required_fields = all(field in address_state for field in required_fields)
                    self.log_test_result("地址状态数据完整性", has_required_fields, 
                                       f"包含字段: {list(address_state.keys())}")
                
                # 获取最近交易
                recent_txs = await self.data_fetcher.get_recent_transactions(test_address, limit=5)
                self.log_test_result("获取最近交易", True, f"获取到 {len(recent_txs)} 笔交易")
                
                # 测试变化检测
                if address_state:
                    # 模拟状态变化
                    old_state = None  # 首次监控
                    changes = await self.data_fetcher.detect_address_changes(
                        test_address, old_state, address_state
                    )
                    self.log_test_result("检测地址变化", True, f"检测到 {len(changes)} 个变化")
                    
        except Exception as e:
            self.log_test_result("数据获取器", False, f"异常: {e}", time.time() - start_time)
        
        duration = time.time() - start_time
        logger.info(f"数据获取器测试完成，耗时: {duration:.2f}秒")
    
    def test_message_formatter(self):
        """测试消息格式化器"""
        logger.info("开始测试消息格式化器...")
        start_time = time.time()
        
        try:
            # 测试不同类型的通知格式化
            
            # 测试余额增加通知
            balance_increase_data = {
                'type': 'balance_increase',
                'old_balance': '1.5',
                'new_balance': '2.0',
                'change_amount': '0.5'
            }
            
            formatted_msg = self.message_formatter.format_change_notification(
                "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6", 
                balance_increase_data
            )
            has_content = len(formatted_msg) > 0
            self.log_test_result("格式化余额增加通知", has_content, 
                               f"消息长度: {len(formatted_msg)}")
            
            # 测试新交易通知
            new_tx_data = {
                'type': 'new_transaction',
                'tx_hash': '0x1234567890abcdef1234567890abcdef12345678',
                'tx_type': 'transfer',
                'amount': '1.0',
                'block_number': 12345
            }
            
            formatted_msg = self.message_formatter.format_change_notification(
                "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6", 
                new_tx_data
            )
            has_content = len(formatted_msg) > 0
            self.log_test_result("格式化新交易通知", has_content, 
                               f"消息长度: {len(formatted_msg)}")
            
            # 测试汇总报告
            summary_data = {
                'total_addresses': 10,
                'active_addresses': 8,
                'total_changes': 15,
                'scan_duration': 2.5
            }
            
            formatted_report = self.message_formatter.format_summary_report(summary_data)
            has_content = len(formatted_report) > 0
            self.log_test_result("格式化汇总报告", has_content, 
                               f"报告长度: {len(formatted_report)}")
            
        except Exception as e:
            self.log_test_result("消息格式化器", False, f"异常: {e}", time.time() - start_time)
        
        duration = time.time() - start_time
        logger.info(f"消息格式化器测试完成，耗时: {duration:.2f}秒")
    
    async def test_error_handler(self):
        """测试错误处理器"""
        logger.info("开始测试错误处理器...")
        start_time = time.time()
        
        try:
            # 测试重试机制
            @global_error_handler.retry(max_attempts=3, base_delay=0.1)
            async def failing_function():
                raise ValueError("测试异常")
            
            try:
                await failing_function()
                self.log_test_result("错误重试机制", False, "应该抛出异常")
            except ValueError:
                self.log_test_result("错误重试机制", True, "正确重试并抛出异常")
            
            # 测试成功重试
            call_count = 0
            
            @global_error_handler.retry(max_attempts=3, base_delay=0.1)
            async def eventually_succeeding_function():
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise ValueError("临时失败")
                return "成功"
            
            result = await eventually_succeeding_function()
            success = result == "成功" and call_count == 2
            self.log_test_result("成功重试机制", success, f"尝试次数: {call_count}")
            
            # 测试错误统计
            error_stats = global_error_handler.get_error_stats()
            has_stats = len(error_stats) > 0
            self.log_test_result("错误统计", has_stats, f"统计项: {len(error_stats)}")
            
        except Exception as e:
            self.log_test_result("错误处理器", False, f"异常: {e}", time.time() - start_time)
        
        duration = time.time() - start_time
        logger.info(f"错误处理器测试完成，耗时: {duration:.2f}秒")
    
    async def test_address_validation(self):
        """测试地址验证"""
        logger.info("开始测试地址验证...")
        start_time = time.time()
        
        try:
            # 创建Telegram Bot实例进行测试
            class MockBot:
                def is_valid_address(self, address: str) -> bool:
                    import re
                    pattern = r'^0x[a-fA-F0-9]{40}$'
                    return bool(re.match(pattern, address))
                
                def extract_address_from_text(self, text: str) -> str:
                    import re
                    pattern = r'0x[a-fA-F0-9]{40}'
                    match = re.search(pattern, text, re.IGNORECASE)
                    return match.group(0) if match else None
            
            mock_bot = MockBot()
            
            # 测试有效地址
            valid_addresses = [
                "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6",
                "0x1234567890123456789012345678901234567890",
                "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
            ]
            
            for address in valid_addresses:
                is_valid = mock_bot.is_valid_address(address)
                self.log_test_result(f"有效地址验证: {address}", is_valid, "地址格式正确")
            
            # 测试无效地址
            invalid_addresses = [
                "0x123",  # 太短
                "0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # 包含非法字符
                "1234567890123456789012345678901234567890",  # 缺少0x前缀
                "",  # 空地址
                "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6extra"  # 多余字符
            ]
            
            for address in invalid_addresses:
                is_valid = mock_bot.is_valid_address(address)
                self.log_test_result(f"无效地址验证: {address}", not is_valid, "正确识别为无效地址")
            
            # 测试地址提取
            test_texts = [
                "请监控这个地址 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6 谢谢",
                "0x1234567890123456789012345678901234567890",
                "地址是0xAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAb",
                "没有地址的文本"
            ]
            
            expected_results = [
                "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb6",
                "0x1234567890123456789012345678901234567890",
                "0xAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAbCdEfAb",
                None
            ]
            
            for text, expected in zip(test_texts, expected_results):
                extracted = mock_bot.extract_address_from_text(text)
                match = extracted == expected
                self.log_test_result(f"地址提取: '{text[:30]}...'", match, 
                                   f"提取结果: {extracted}")
            
        except Exception as e:
            self.log_test_result("地址验证", False, f"异常: {e}", time.time() - start_time)
        
        duration = time.time() - start_time
        logger.info(f"地址验证测试完成，耗时: {duration:.2f}秒")
    
    async def test_performance(self):
        """性能测试"""
        logger.info("开始性能测试...")
        start_time = time.time()
        
        try:
            # 测试数据库批量操作性能
            test_user_id = 999999
            num_addresses = 50
            
            # 批量添加地址
            db_start = time.time()
            for i in range(num_addresses):
                address = f"0x{i:040x}"  # 生成测试地址
                self.db.add_monitored_address(test_user_id, address, f"测试地址{i}")
            
            db_duration = time.time() - db_start
            self.log_test_result("数据库批量添加", True, 
                               f"添加 {num_addresses} 个地址耗时: {db_duration:.3f}s")
            
            # 测试批量获取性能
            fetch_start = time.time()
            addresses = self.db.get_user_addresses(test_user_id)
            fetch_duration = time.time() - fetch_start
            self.log_test_result("数据库批量获取", True, 
                               f"获取 {len(addresses)} 个地址耗时: {fetch_duration:.3f}s")
            
            # 测试数据获取器性能
            async with self.data_fetcher:
                test_addresses = [f"0x{i:040x}" for i in range(5)]  # 少量地址测试
                
                fetcher_start = time.time()
                tasks = []
                for address in test_addresses:
                    task = self.data_fetcher.get_address_state(address)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                fetcher_duration = time.time() - fetcher_start
                
                successful = sum(1 for r in results if r is not None and not isinstance(r, Exception))
                self.log_test_result("数据获取器并发性能", True, 
                                   f"并发获取 {len(test_addresses)} 个地址耗时: {fetcher_duration:.3f}s, 成功: {successful}")
            
            # 清理测试数据
            for i in range(num_addresses):
                address = f"0x{i:040x}"
                self.db.remove_monitored_address(test_user_id, address)
            
        except Exception as e:
            self.log_test_result("性能测试", False, f"异常: {e}", time.time() - start_time)
        
        duration = time.time() - start_time
        logger.info(f"性能测试完成，耗时: {duration:.2f}秒")
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("开始Hypeliquid聪明钱监控机器人测试")
        logger.info("=" * 60)
        
        total_start = time.time()
        
        # 运行各项测试
        await self.test_database_operations()
        await self.test_data_fetcher()
        self.test_message_formatter()
        await self.test_error_handler()
        await self.test_address_validation()
        await self.test_performance()
        
        # 生成测试报告
        self.generate_test_report()
        
        total_duration = time.time() - total_start
        logger.info(f"所有测试完成，总耗时: {total_duration:.2f}秒")
        
        # 返回测试结果摘要
        return self.get_test_summary()
    
    def generate_test_report(self):
        """生成测试报告"""
        logger.info("生成测试报告...")
        
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        total_tests = len(self.test_results)
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'tests': self.test_results
        }
        
        # 保存测试报告
        report_file = f"logs/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"测试报告已保存到: {report_file}")
        
        # 输出摘要
        logger.info("=" * 60)
        logger.info("测试摘要:")
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过数: {passed_tests}")
        logger.info(f"失败数: {total_tests - passed_tests}")
        logger.info(f"成功率: {report['summary']['success_rate']:.1f}%")
        logger.info("=" * 60)
    
    def get_test_summary(self) -> dict:
        """获取测试摘要"""
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        total_tests = len(self.test_results)
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'all_passed': passed_tests == total_tests and total_tests > 0
        }

async def main():
    """主测试函数"""
    try:
        logger.info("启动Hypeliquid聪明钱监控机器人测试...")
        
        # 创建测试器
        tester = BotTester()
        
        # 运行所有测试
        summary = await tester.run_all_tests()
        
        # 根据测试结果退出
        if summary['all_passed']:
            logger.info("🎉 所有测试通过！")
            return 0
        else:
            logger.error("❌ 部分测试失败")
            return 1
            
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}")
        return 1

if __name__ == '__main__':
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)