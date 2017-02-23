import time

def retry(times, sleep=0, exclude_exceptions=[]):
    def decorator(func):
        def wrapper(*args, **kwargs):
            run_times = 0
            while 1:
                try:
                    time.sleep(sleep)
                    return func(*args, **kwargs)
                except Exception as ex:
                    if run_times < times:
                        run_times += 1
                    else:
                        raise ex
        return wrapper
    return decorator