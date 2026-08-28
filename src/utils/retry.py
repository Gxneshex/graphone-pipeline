import time
import random
import logging
from functools import wraps
from typing import Callable, Any, Tuple, Type

logger = logging.getLogger("graphone-pipeline.retry")

def retry_with_backoff(
    retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,)
) -> Callable:
    """
    Decorator that retries a synchronous function using exponential backoff with jitter.
    
    Formula: delay = min(max_delay, base_delay * (2 ** attempt)) + jitter
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt > retries:
                        logger.error(f"Function {func.__name__} failed permanently after {retries} retries. Error: {e}")
                        raise e
                    
                    # Calculate exponential delay
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    # Add randomized full jitter to avoid thundering herd problem
                    jitter = random.uniform(0, delay)
                    total_delay = delay + jitter
                    
                    logger.warning(
                        f"Target broken or rate-limited ({e}). "
                        f"Retrying {func.__name__} (Attempt {attempt}/{retries}) in {total_delay:.2f} seconds..."
                    )
                    time.sleep(total_delay)
        return wrapper
    return decorator
