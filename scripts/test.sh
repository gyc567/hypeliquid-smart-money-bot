#!/bin/bash

# Hypeliquid聪明钱监控机器人测试脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数：输出带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：检查Python环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3未安装"
        exit 1
    fi
    
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3未安装"
        exit 1
    fi
}

# 函数：运行测试
run_tests() {
    print_info "开始运行测试..."
    
    # 创建日志目录
    mkdir -p logs
    
    # 运行测试
    if python3 test_bot.py; then
        print_success "测试通过！"
        return 0
    else
        print_error "测试失败！"
        return 1
    fi
}

# 函数：运行单元测试
run_unit_tests() {
    print_info "运行单元测试..."
    
    # 检查pytest是否安装
    if ! python3 -m pytest --version &> /dev/null; then
        print_info "安装pytest..."
        pip3 install pytest pytest-asyncio
    fi
    
    # 运行pytest
    if python3 -m pytest tests/ -v; then
        print_success "单元测试通过！"
        return 0
    else
        print_error "单元测试失败！"
        return 1
    fi
}

# 函数：性能测试
run_performance_test() {
    print_info "运行性能测试..."
    
    # 创建性能测试脚本
    cat > performance_test.py << 'EOF'
#!/usr/bin/env python3

import asyncio
import time
import logging
from database import DatabaseManager
from data_fetcher import HyperliquidDataFetcher
from monitor import AddressMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def performance_test():
    """性能测试"""
    logger.info("开始性能测试...")
    
    # 初始化组件
    db = DatabaseManager("test_performance.db")
    fetcher = HyperliquidDataFetcher()
    monitor = AddressMonitor(db)
    
    # 测试数据库性能
    start_time = time.time()
    
    # 批量添加测试数据
    num_users = 10
    num_addresses_per_user = 20
    total_addresses = num_users * num_addresses_per_user
    
    logger.info(f"测试数据: {num_users} 用户, {total_addresses} 地址")
    
    # 添加测试用户和地址
    for user_id in range(1, num_users + 1):
        db.add_user(user_id, f"test_user_{user_id}")
        
        for addr_id in range(num_addresses_per_user):
            address = f"0x{user_id:08x}{addr_id:032x}"
            db.add_monitored_address(user_id, address, f"地址_{user_id}_{addr_id}")
    
    db_duration = time.time() - start_time
    logger.info(f"数据库初始化耗时: {db_duration:.3f}s")
    
    # 测试地址扫描性能
    async with fetcher:
        start_time = time.time()
        
        # 获取所有活跃地址
        active_addresses = db.get_all_active_addresses()
        logger.info(f"活跃地址数: {len(active_addresses)}")
        
        # 模拟扫描部分地址
        test_addresses = active_addresses[:10]  # 只测试前10个地址
        
        tasks = []
        for address in test_addresses:
            task = fetcher.get_address_state(address)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        scan_duration = time.time() - start_time
        successful = sum(1 for r in results if r is not None and not isinstance(r, Exception))
        
        logger.info(f"扫描 {len(test_addresses)} 个地址耗时: {scan_duration:.3f}s")
        logger.info(f"成功获取: {successful}/{len(test_addresses)}")
        logger.info(f"平均每个地址: {scan_duration/len(test_addresses):.3f}s")
    
    # 性能指标
    logger.info("性能指标:")
    logger.info(f"数据库操作: {total_addresses} 地址 / {db_duration:.3f}s = {total_addresses/db_duration:.1f} 地址/秒")
    logger.info(f"数据获取: {len(test_addresses)} 地址 / {scan_duration:.3f}s = {len(test_addresses)/scan_duration:.1f} 地址/秒")
    
    # 清理测试数据
    import os
    if os.path.exists("test_performance.db"):
        os.remove("test_performance.db")
    
    logger.info("性能测试完成")

if __name__ == '__main__':
    asyncio.run(performance_test())
EOF
    
    if python3 performance_test.py; then
        print_success "性能测试完成！"
        rm -f performance_test.py test_performance.db
        return 0
    else
        print_error "性能测试失败！"
        return 1
    fi
}

# 函数：压力测试
run_stress_test() {
    print_info "运行压力测试..."
    
    # 创建压力测试脚本
    cat > stress_test.py << 'EOF'
#!/usr/bin/env python3

import asyncio
import time
import logging
import aiohttp
from database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def stress_test():
    """压力测试"""
    logger.info("开始压力测试...")
    
    db = DatabaseManager("test_stress.db")
    
    # 测试参数
    num_operations = 1000
    concurrent_operations = 50
    
    logger.info(f"测试参数: {num_operations} 操作, {concurrent_operations} 并发")
    
    # 数据库压力测试
    start_time = time.time()
    
    async def db_operation(i):
        """单个数据库操作"""
        try:
            user_id = 1000 + i
            address = f"0x{i:040x}"
            
            # 添加用户和地址
            db.add_user(user_id, f"stress_user_{i}")
            db.add_monitored_address(user_id, address, f"stress_addr_{i}")
            
            # 查询操作
            addresses = db.get_user_addresses(user_id)
            
            return len(addresses) > 0
        except Exception as e:
            logger.error(f"操作 {i} 失败: {e}")
            return False
    
    # 并发执行操作
    semaphore = asyncio.Semaphore(concurrent_operations)
    
    async def bounded_operation(i):
        async with semaphore:
            return await db_operation(i)
    
    tasks = [bounded_operation(i) for i in range(num_operations)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.time() - start_time
    
    # 统计结果
    successful = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if isinstance(r, Exception))
    
    logger.info("压力测试结果:")
    logger.info(f"总操作数: {num_operations}")
    logger.info(f"成功: {successful}")
    logger.info(f"失败: {num_operations - successful - failed}")
    logger.info(f"异常: {failed}")
    logger.info(f"总耗时: {duration:.3f}s")
    logger.info(f"平均每秒操作: {num_operations/duration:.1f}")
    logger.info(f"成功率: {successful/num_operations*100:.1f}%")
    
    # 清理测试数据
    import os
    if os.path.exists("test_stress.db"):
        os.remove("test_stress.db")
    
    logger.info("压力测试完成")

if __name__ == '__main__':
    asyncio.run(stress_test())
EOF
    
    if python3 stress_test.py; then
        print_success "压力测试完成！"
        rm -f stress_test.py test_stress.db
        return 0
    else
        print_error "压力测试失败！"
        return 1
    fi
}

# 函数：显示帮助信息
show_help() {
    echo "Hypeliquid聪明钱监控机器人测试脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  --all           运行所有测试（默认）"
    echo "  --unit          运行单元测试"
    echo "  --performance   运行性能测试"
    echo "  --stress        运行压力测试"
    echo "  --help          显示帮助信息"
    echo
    echo "示例:"
    echo "  $0              # 运行所有测试"
    echo "  $0 --unit       # 运行单元测试"
    echo "  $0 --performance # 运行性能测试"
}

# 主函数
main() {
    # 默认运行所有测试
    TEST_TYPE="all"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                TEST_TYPE="all"
                shift
                ;;
            --unit)
                TEST_TYPE="unit"
                shift
                ;;
            --performance)
                TEST_TYPE="performance"
                shift
                ;;
            --stress)
                TEST_TYPE="stress"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查Python环境
    check_python
    
    print_info "开始Hypeliquid聪明钱监控机器人测试..."
    
    # 运行相应的测试
    case $TEST_TYPE in
        all)
            run_tests && run_unit_tests && run_performance_test && run_stress_test
            ;;
        unit)
            run_unit_tests
            ;;
        performance)
            run_performance_test
            ;;
        stress)
            run_stress_test
            ;;
        *)
            print_error "未知测试类型: $TEST_TYPE"
            show_help
            exit 1
            ;;
    esac
    
    print_success "测试完成！"
}

# 脚本入口
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi