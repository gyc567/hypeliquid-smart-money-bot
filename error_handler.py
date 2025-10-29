import asyncio
import logging
import time
import traceback
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime, timedelta
from functools import wraps
import random

logger = logging.getLogger(__name__)

class RetryConfig:
    """重试配置"""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True,
                 exceptions: tuple = (Exception,)):
        """
        初始化重试配置
        
        Args:
            max_attempts: 最大重试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            exponential_base: 指数退避基数
            jitter: 是否添加随机抖动
            exceptions: 需要重试的异常类型
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.exceptions = exceptions

class ErrorHandler:
    """错误处理器 - 统一的错误处理和重试机制"""
    
    def __init__(self, 
                 default_retry_config: Optional[RetryConfig] = None,
                 max_error_log_size: int = 1000):
        self.default_retry_config = default_retry_config or RetryConfig()
        self.error_log: List[Dict] = []
        self.max_error_log_size = max_error_log_size
        self.error_stats = {
            'total_errors': 0,
            'retried_errors': 0,
            'recovered_errors': 0,
            'fatal_errors': 0,
            'last_error_time': None
        }
    
    def retry(self, 
              retry_config: Optional[RetryConfig] = None,
              fallback: Optional[Callable] = None,
              context: Optional[Dict] = None):
        """
        重试装饰器
        
        Args:
            retry_config: 重试配置（使用默认配置如果为None）
            fallback: 失败时的回退函数
            context: 额外的上下文信息
        """
        config = retry_config or self.default_retry_config
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """异步函数包装器"""
                return await self._retry_async(
                    func, config, fallback, context, *args, **kwargs
                )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """同步函数包装器"""
                return self._retry_sync(
                    func, config, fallback, context, *args, **kwargs
                )
            
            # 根据函数类型返回适当的包装器
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    async def _retry_async(self, func: Callable, config: RetryConfig, 
                          fallback: Optional[Callable], context: Optional[Dict], 
                          *args, **kwargs) -> Any:
        """异步重试逻辑"""
        last_exception = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 如果之前失败过，记录恢复
                if attempt > 1:
                    self.error_stats['recovered_errors'] += 1
                    logger.info(f"函数 {func.__name__} 在第 {attempt} 次尝试时恢复成功")
                
                return result
                
            except config.exceptions as e:
                last_exception = e
                self.error_stats['total_errors'] += 1
                self.error_stats['retried_errors'] += 1
                self.error_stats['last_error_time'] = datetime.now()
                
                # 记录错误
                self._log_error(func.__name__, e, attempt, config.max_attempts, context)
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < config.max_attempts:
                    delay = self._calculate_delay(attempt, config)
                    logger.warning(f"函数 {func.__name__} 第 {attempt} 次尝试失败，{delay:.1f}秒后重试: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"函数 {func.__name__} 在 {config.max_attempts} 次尝试后仍然失败: {e}")
            
            except Exception as e:
                # 非重试异常，直接抛出
                logger.error(f"函数 {func.__name__} 遇到非重试异常: {e}")
                raise
        
        # 所有重试都失败
        self.error_stats['fatal_errors'] += 1
        
        # 尝试回退函数
        if fallback:
            try:
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                else:
                    return fallback(*args, **kwargs)
            except Exception as e:
                logger.error(f"回退函数也失败: {e}")
        
        # 抛出最后的异常
        raise last_exception
    
    def _retry_sync(self, func: Callable, config: RetryConfig, 
                   fallback: Optional[Callable], context: Optional[Dict], 
                   *args, **kwargs) -> Any:
        """同步重试逻辑"""
        last_exception = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 如果之前失败过，记录恢复
                if attempt > 1:
                    self.error_stats['recovered_errors'] += 1
                    logger.info(f"函数 {func.__name__} 在第 {attempt} 次尝试时恢复成功")
                
                return result
                
            except config.exceptions as e:
                last_exception = e
                self.error_stats['total_errors'] += 1
                self.error_stats['retried_errors'] += 1
                self.error_stats['last_error_time'] = datetime.now()
                
                # 记录错误
                self._log_error(func.__name__, e, attempt, config.max_attempts, context)
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < config.max_attempts:
                    delay = self._calculate_delay(attempt, config)
                    logger.warning(f"函数 {func.__name__} 第 {attempt} 次尝试失败，{delay:.1f}秒后重试: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"函数 {func.__name__} 在 {config.max_attempts} 次尝试后仍然失败: {e}")
            
            except Exception as e:
                # 非重试异常，直接抛出
                logger.error(f"函数 {func.__name__} 遇到非重试异常: {e}")
                raise
        
        # 所有重试都失败
        self.error_stats['fatal_errors'] += 1
        
        # 尝试回退函数
        if fallback:
            try:
                return fallback(*args, **kwargs)
            except Exception as e:
                logger.error(f"回退函数也失败: {e}")
        
        # 抛出最后的异常
        raise last_exception
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """计算重试延迟时间"""
        # 指数退避
        delay = config.base_delay * (config.exponential_base ** (attempt - 1))
        
        # 限制最大延迟
        delay = min(delay, config.max_delay)
        
        # 添加随机抖动
        if config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def _log_error(self, function_name: str, error: Exception, 
                   attempt: int, max_attempts: int, context: Optional[Dict]):
        """记录错误信息"""
        error_info = {
            'timestamp': datetime.now(),
            'function': function_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'attempt': attempt,
            'max_attempts': max_attempts,
            'context': context or {},
            'traceback': traceback.format_exc()
        }
        
        # 添加到错误日志
        self.error_log.append(error_info)
        
        # 限制错误日志大小
        if len(self.error_log) > self.max_error_log_size:
            self.error_log = self.error_log[-self.max_error_log_size:]
        
        # 记录到标准日志
        logger.error(f"错误记录 - 函数: {function_name}, 尝试: {attempt}/{max_attempts}, "
                    f"错误: {type(error).__name__}: {error}")
    
    def get_error_stats(self) -> Dict:
        """获取错误统计信息"""
        return {
            **self.error_stats,
            'recent_errors': len(self.error_log),
            'error_rate_24h': self._calculate_error_rate_24h(),
            'recovery_rate': self._calculate_recovery_rate()
        }
    
    def _calculate_error_rate_24h(self) -> float:
        """计算24小时错误率"""
        if not self.error_stats['last_error_time']:
            return 0.0
        
        # 这里简化计算，实际需要更复杂的逻辑
        recent_errors = [
            error for error in self.error_log
            if (datetime.now() - error['timestamp']).total_seconds() < 86400
        ]
        
        return len(recent_errors) / max(len(self.error_log), 1) * 100
    
    def _calculate_recovery_rate(self) -> float:
        """计算错误恢复率"""
        total_errors = self.error_stats['total_errors']
        recovered_errors = self.error_stats['recovered_errors']
        
        if total_errors == 0:
            return 100.0
        
        return (recovered_errors / total_errors) * 100
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """获取最近的错误记录"""
        return self.error_log[-limit:] if self.error_log else []
    
    def clear_error_log(self):
        """清空错误日志"""
        self.error_log.clear()
        logger.info("错误日志已清空")


class CircuitBreaker:
    """熔断器 - 防止故障蔓延"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: type = Exception):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
            expected_exception: 预期的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    def __call__(self, func: Callable) -> Callable:
        """装饰器"""
        if asyncio.iscoroutinefunction(func):
            return self._async_wrapper(func)
        else:
            return self._sync_wrapper(func)
    
    def _async_wrapper(self, func: Callable) -> Callable:
        """异步包装器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not self._can_execute():
                raise Exception(f"熔断器开启，拒绝执行 {func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _sync_wrapper(self, func: Callable) -> Callable:
        """同步包装器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self._can_execute():
                raise Exception(f"熔断器开启，拒绝执行 {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _can_execute(self) -> bool:
        """检查是否可以执行"""
        if self.state == 'closed':
            return True
        
        if self.state == 'open':
            # 检查是否到了恢复时间
            if self.last_failure_time:
                time_since_failure = time.time() - self.last_failure_time.timestamp()
                if time_since_failure >= self.recovery_timeout:
                    self.state = 'half-open'
                    logger.info("熔断器进入半开状态")
                    return True
            return False
        
        if self.state == 'half-open':
            return True
        
        return False
    
    def _on_success(self):
        """处理成功"""
        if self.state == 'half-open':
            self.state = 'closed'
            self.failure_count = 0
            logger.info("熔断器关闭，服务恢复正常")
        
        # 连续成功时逐渐减少失败计数
        if self.failure_count > 0:
            self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self):
        """处理失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"熔断器开启，失败次数: {self.failure_count}")
    
    def get_state(self) -> str:
        """获取熔断器状态"""
        return self.state
    
    def reset(self):
        """重置熔断器"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'
        logger.info("熔断器已重置")


# 全局错误处理器实例
global_error_handler = ErrorHandler()

# 常用的重试配置
RETRY_CONFIGS = {
    'network': RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(ConnectionError, TimeoutError, aiohttp.ClientError)
    ),
    'api': RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=10.0,
        exceptions=(ValueError, KeyError, json.JSONDecodeError)
    ),
    'database': RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
        exceptions=(sqlite3.Error, DatabaseError)
    ),
    'critical': RetryConfig(
        max_attempts=10,
        base_delay=1.0,
        max_delay=60.0,
        exceptions=(Exception,)
    )
}

# 常用的熔断器配置
CIRCUIT_BREAKER_CONFIGS = {
    'api': CircuitBreaker(
        failure_threshold=10,
        recovery_timeout=60.0,
        expected_exception=aiohttp.ClientError
    ),
    'database': CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=30.0,
        expected_exception=sqlite3.Error
    ),
    'external_service': CircuitBreaker(
        failure_threshold=15,
        recovery_timeout=120.0,
        expected_exception=ConnectionError
    )
}

# 快捷装饰器
def retry_network_operation(func: Callable) -> Callable:
    """网络操作重试装饰器"""
    return global_error_handler.retry(
        retry_config=RETRY_CONFIGS['network'],
        context={'operation_type': 'network'}
    )(func)

def retry_api_operation(func: Callable) -> Callable:
    """API操作重试装饰器"""
    return global_error_handler.retry(
        retry_config=RETRY_CONFIGS['api'],
        context={'operation_type': 'api'}
    )(func)

def retry_database_operation(func: Callable) -> Callable:
    """数据库操作重试装饰器"""
    return global_error_handler.retry(
        retry_config=RETRY_CONFIGS['database'],
        context={'operation_type': 'database'}
    )(func)

def circuit_breaker_api(func: Callable) -> Callable:
    """API熔断器装饰器"""
    return CIRCUIT_BREAKER_CONFIGS['api'](func)

def circuit_breaker_database(func: Callable) -> Callable:
    """数据库熔断器装饰器"""
    return CIRCUIT_BREAKER_CONFIGS['database'](func)

# 数据库错误类
class DatabaseError(Exception):
    """数据库操作错误"""
    pass

class DataValidationError(Exception):
    """数据验证错误"""
    pass

class APIError(Exception):
    """API调用错误"""
    pass

class ConfigurationError(Exception):
    """配置错误"""
    pass

# 错误处理工具函数
def log_exception(func_name: str, exception: Exception, context: Optional[Dict] = None):
    """记录异常信息"""
    error_info = {
        'function': func_name,
        'error_type': type(exception).__name__,
        'error_message': str(exception),
        'context': context or {},
        'timestamp': datetime.now(),
        'traceback': traceback.format_exc()
    }
    
    logger.error(f"异常记录 - 函数: {func_name}, 错误: {type(exception).__name__}: {exception}")
    return error_info

def safe_execute(func: Callable, fallback: Any = None, *args, **kwargs):
    """安全执行函数，捕获所有异常"""
    try:
        if asyncio.iscoroutinefunction(func):
            # 异步函数需要特殊处理
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已经在运行，使用create_task
                return asyncio.create_task(func(*args, **kwargs))
            else:
                # 否则直接运行
                return loop.run_until_complete(func(*args, **kwargs))
        else:
            # 同步函数
            return func(*args, **kwargs)
    except Exception as e:
        log_exception(func.__name__ if hasattr(func, '__name__') else 'unknown', e)
        return fallback

def validate_config(required_keys: List[str], config: Dict, config_name: str = "配置"):
    """验证配置完整性"""
    missing_keys = [key for key in required_keys if key not in config or config[key] is None]
    
    if missing_keys:
        raise ConfigurationError(f"{config_name}缺少必需的配置项: {', '.join(missing_keys)}")

# 监控和报警相关的错误处理
class AlertManager:
    """警报管理器 - 处理系统异常和发送警报"""
    
    def __init__(self, bot_token: str = None, admin_chat_id: str = None):
        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id
        self.alert_cooldown = {}  # 警报冷却时间
        self.cooldown_period = 3600  # 1小时冷却期
    
    async def send_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """发送警报"""
        try:
            # 检查冷却时间
            if self._is_in_cooldown(alert_type):
                return
            
            # 格式化警报消息
            alert_message = self._format_alert_message(alert_type, message, severity)
            
            # 这里可以实现发送逻辑，比如通过Telegram Bot
            # 暂时只记录日志
            if severity == 'critical':
                logger.critical(f"系统警报 - {alert_type}: {message}")
            elif severity == 'error':
                logger.error(f"系统警报 - {alert_type}: {message}")
            else:
                logger.warning(f"系统警报 - {alert_type}: {message}")
            
            # 更新冷却时间
            self._update_cooldown(alert_type)
            
        except Exception as e:
            logger.error(f"发送警报失败: {e}")
    
    def _is_in_cooldown(self, alert_type: str) -> bool:
        """检查是否处于冷却期"""
        if alert_type not in self.alert_cooldown:
            return False
        
        last_alert_time = self.alert_cooldown[alert_type]
        time_since_last = (datetime.now() - last_alert_time).total_seconds()
        
        return time_since_last < self.cooldown_period
    
    def _update_cooldown(self, alert_type: str):
        """更新冷却时间"""
        self.alert_cooldown[alert_type] = datetime.now()
    
    def _format_alert_message(self, alert_type: str, message: str, severity: str) -> str:
        """格式化警报消息"""
        severity_emojis = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }
        
        emoji = severity_emojis.get(severity, '⚠️')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""
{emoji} **系统警报 - {alert_type.upper()}**

严重程度: {severity}
时间: {timestamp}

{message}
        """.strip()

# 创建全局警报管理器实例
global_alert_manager = AlertManager()

# 快捷函数
async def send_system_alert(alert_type: str, message: str, severity: str = 'warning'):
    """发送系统警报"""
    await global_alert_manager.send_alert(alert_type, message, severity)

def log_and_handle_error(error: Exception, context: Optional[Dict] = None):
    """记录并处理错误"""
    error_info = log_exception('unknown', error, context)
    
    # 根据错误类型决定是否需要发送警报
    if isinstance(error, (APIError, DatabaseError)):
        asyncio.create_task(send_system_alert(
            'service_error',
            f"服务错误: {error}",
            'error'
        ))
    
    elif isinstance(error, ConfigurationError):
        asyncio.create_task(send_system_alert(
            'config_error',
            f"配置错误: {error}",
            'critical'
        ))
    
    return error_info