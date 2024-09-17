from functools import wraps
import time


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        print(f'Call {func.__name__} seconds\n\t{args=}\n\t{kwargs=} ')
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'End {func.__name__} Took {total_time:.4f} ')
        return result
    return timeit_wrapper

def timeit_async(func):
    @wraps(func)
    async def timeit_wrapper(*args, **kwargs):
        print(f'Call {func.__name__} seconds\n\t{args=}\n\t{kwargs=} ')
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'End {func.__name__} Took {total_time:.4f} ')
        return result
    return timeit_wrapper
