import time


def wait_until(somepredicate, timeout, period=0.1, *args, **kwargs):
  
  if timeout is None:
    while True:
        if somepredicate(*args, **kwargs): 
            return True
        time.sleep(period)
    return False      
  else:
    mustend = time.time() + timeout
    while time.time() < mustend:
        if somepredicate(*args, **kwargs): 
            return True
        time.sleep(period)
    return False