import functools
import time

from loading_pipeline.lib.logger import get_logger

logger = get_logger(__name__)


def retry(tries=3, delay=30, backoff=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            max_tries = tries
            current_delay = delay
            total_start_time = time.time()
            args_str = ', '.join(str(a) for a in args)
            kwargs_str = ', '.join(f'{k}={v!s}' for k, v in kwargs.items())

            for attempt in range(1, max_tries):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.info(
                        f'{func.__name__} args:{args_str} kwargs:{kwargs_str} succeeded on attempt {attempt} in {duration:.2f}s',
                    )
                except Exception:
                    duration = time.time() - start_time
                    logger.exception(
                        f'{func.__name__} args:{args_str} kwargs:{kwargs_str} failed on attempt {attempt} after {duration:.2f}s, '
                        f'retrying in {current_delay} seconds.',
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                else:
                    return result

            # Final attempt
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                total_duration = time.time() - total_start_time
                logger.info(
                    f'{func.__name__} args:{args_str} kwargs:{kwargs_str} succeeded on final attempt {max_tries} in {duration:.2f}s '
                    f'(total retry time: {total_duration:.2f}s)',
                )
            except Exception:
                duration = time.time() - start_time
                total_duration = time.time() - total_start_time
                logger.exception(
                    f'{func.__name__} args:{args_str} kwargs:{kwargs} failed on final attempt {max_tries} after {duration:.2f}s '
                    f'(total retry time: {total_duration:.2f}s)',
                )
                raise
            else:
                return result

        return wrapper

    return decorator
