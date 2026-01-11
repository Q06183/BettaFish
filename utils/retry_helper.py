"""
重试机制工具模块
提供通用的网络请求重试功能，增强系统健壮性
"""

import time
from functools import wraps
from typing import Callable, Any
import requests
from loguru import logger

# 配置日志
class RetryConfig:
    """重试配置类"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        retry_on_exceptions: tuple = None
    ):
        """
        初始化重试配置
        
        Args:
            max_retries: 最大重试次数
            initial_delay: 初始延迟秒数
            backoff_factor: 退避因子（每次重试延迟翻倍）
            max_delay: 最大延迟秒数
            retry_on_exceptions: 需要重试的异常类型元组
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        
        # 默认需要重试的异常类型
        if retry_on_exceptions is None:
            self.retry_on_exceptions = (
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
                requests.exceptions.Timeout,
                requests.exceptions.TooManyRedirects,
                ConnectionError,
                TimeoutError,
                Exception  # OpenAI和其他API可能抛出的一般异常
            )
        else:
            self.retry_on_exceptions = retry_on_exceptions

# 默认配置
DEFAULT_RETRY_CONFIG = RetryConfig()

def with_retry(config: RetryConfig = None):
    """
    重试装饰器
    
    Args:
        config: 重试配置，如果不提供则使用默认配置
    
    Returns:
        装饰器函数
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):  # +1 因为第一次不算重试
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"函数 {func.__name__} 在第 {attempt + 1} 次尝试后成功")
                    return result
                    
                except config.retry_on_exceptions as e:
                    last_exception = e
                    error_str = str(e)

                    # 检查是否为不可重试的错误（如内容安全拦截）
                    if "inappropriate content" in error_str or "Output data may contain inappropriate content" in error_str:
                        logger.warning(f"函数 {func.__name__} 遇到内容安全拦截: {error_str}")
                        
                        if attempt < config.max_retries:
                            logger.info("尝试追加安全提示并重试...")
                            # 尝试修改输入参数，追加安全提示
                            try:
                                safety_notice = "\n\n【系统安全提示：请务必确保生成的内容客观、中立、合规，严禁包含任何色情、暴力、政治敏感或其他不当内容。请对输出进行脱敏处理。】"
                                
                                # 修改位置参数
                                new_args = list(args)
                                for i, arg in enumerate(new_args):
                                    if isinstance(arg, str) and len(arg) > 5 and safety_notice not in arg:
                                        new_args[i] = arg + safety_notice
                                args = tuple(new_args)
                                
                                # 修改关键字参数
                                for key, value in kwargs.items():
                                    if isinstance(value, str) and len(value) > 5 and safety_notice not in value:
                                        kwargs[key] = value + safety_notice
                                        
                                # 短暂等待后重试
                                time.sleep(1.0)
                                continue
                            except Exception as sanitize_err:
                                logger.error(f"尝试修复参数失败: {sanitize_err}")
                                raise e
                        else:
                            logger.error(f"函数 {func.__name__} 遇到内容安全拦截，且已达到最大重试次数")
                            raise e
                    
                    if attempt == config.max_retries:
                        # 最后一次尝试也失败了
                        logger.error(f"函数 {func.__name__} 在 {config.max_retries + 1} 次尝试后仍然失败")
                        logger.error(f"最终错误: {str(e)}")
                        raise e
                    
                    # 计算延迟时间
                    delay = min(
                        config.initial_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )
                    
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}")
                    logger.info(f"将在 {delay:.1f} 秒后进行第 {attempt + 2} 次尝试...")
                    
                    time.sleep(delay)
                
                except Exception as e:
                    # 不在重试列表中的异常，直接抛出
                    logger.error(f"函数 {func.__name__} 遇到不可重试的异常: {str(e)}")
                    raise e
            
            # 这里不应该到达，但作为安全网
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator

def retry_on_network_error(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """
    专门用于网络错误的重试装饰器（简化版）
    
    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟秒数
        backoff_factor: 退避因子
    
    Returns:
        装饰器函数
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor
    )
    return with_retry(config)

class RetryableError(Exception):
    """自定义的可重试异常"""
    pass

def with_graceful_retry(config: RetryConfig = None, default_return=None):
    """
    优雅重试装饰器 - 用于非关键API调用
    失败后不会抛出异常，而是返回默认值，保证系统继续运行
    
    Args:
        config: 重试配置，如果不提供则使用默认配置
        default_return: 所有重试失败后返回的默认值
    
    Returns:
        装饰器函数
    """
    if config is None:
        config = SEARCH_API_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):  # +1 因为第一次不算重试
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"非关键API {func.__name__} 在第 {attempt + 1} 次尝试后成功")
                    return result
                    
                except config.retry_on_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        # 最后一次尝试也失败了，返回默认值而不抛出异常
                        logger.warning(f"非关键API {func.__name__} 在 {config.max_retries + 1} 次尝试后仍然失败")
                        logger.warning(f"最终错误: {str(e)}")
                        logger.info(f"返回默认值以保证系统继续运行: {default_return}")
                        return default_return
                    
                    # 计算延迟时间
                    delay = min(
                        config.initial_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )
                    
                    logger.warning(f"非关键API {func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}")
                    logger.info(f"将在 {delay:.1f} 秒后进行第 {attempt + 2} 次尝试...")
                    
                    time.sleep(delay)
                
                except Exception as e:
                    # 不在重试列表中的异常，返回默认值
                    logger.warning(f"非关键API {func.__name__} 遇到不可重试的异常: {str(e)}")
                    logger.info(f"返回默认值以保证系统继续运行: {default_return}")
                    return default_return
            
            # 这里不应该到达，但作为安全网
            return default_return
            
        return wrapper
    return decorator

def make_retryable_request(
    request_func: Callable,
    *args,
    max_retries: int = 5,
    **kwargs
) -> Any:
    """
    直接执行可重试的请求（不使用装饰器）
    
    Args:
        request_func: 要执行的请求函数
        *args: 传递给请求函数的位置参数
        max_retries: 最大重试次数
        **kwargs: 传递给请求函数的关键字参数
    
    Returns:
        请求函数的返回值
    """
    config = RetryConfig(max_retries=max_retries)
    
    @with_retry(config)
    def _execute():
        return request_func(*args, **kwargs)
    
    return _execute()

# 预定义一些常用的重试配置
LLM_RETRY_CONFIG = RetryConfig(
    max_retries=6,        # 保持额外重试次数
    initial_delay=60.0,   # 首次等待至少 1 分钟
    backoff_factor=2.0,   # 继续使用指数退避
    max_delay=600.0       # 单次等待最长 10 分钟
)

SEARCH_API_RETRY_CONFIG = RetryConfig(
    max_retries=5,        # 增加到5次重试
    initial_delay=2.0,    # 增加初始延迟
    backoff_factor=1.6,   # 调整退避因子
    max_delay=25.0        # 增加最大延迟
)

DB_RETRY_CONFIG = RetryConfig(
    max_retries=5,        # 增加到5次重试
    initial_delay=1.0,    # 保持较短的数据库重试延迟
    backoff_factor=1.5,
    max_delay=10.0
)
