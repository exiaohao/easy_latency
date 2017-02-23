from gevent import monkey
monkey.patch_all()

import os
import re
import subprocess
import time
import yaml
import gevent
from influx import InfluxLogger

from gevent.pool import Pool
from gevent.subprocess import Popen, PIPE

def read_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def parse_ping(target_name, result):
    line = result.decode().split('\n')
    latency_pattern = re.compile('\d{1,3}.\d{1,3}/\d{1,3}.\d{1,3}/\d{1,3}.\d{1,3}')
    latency = re.findall(latency_pattern, line[-1])
    if len(latency):
        min, avg, max = latency[0].split('/')
    else:
        min, avg, max = 0, 0, 0
    
    il.log('ping', target_name, {'min':min, 'avg': avg, 'max':max})

def make_ping(target_name, addr, times):
    _cmd = ("ping", str(addr), "-c", str(times))
    worker = Popen(' '.join(_cmd), stdout=PIPE, shell=True)
    out, err = worker.communicate()
    parse_ping(target_name, out.rstrip())

def run_server(config):
    ping_times = config['monitor']['ping_times']
    ping_tasks = config['monitor']['ping']
    workers = [gevent.spawn(make_ping, target_name, addr, ping_times) for target_name, addr in ping_tasks.items()]
    gevent.joinall(workers)

if __name__ == "__main__":
    while(1):
        config = read_config()
        il = InfluxLogger(config)
        run_server(config)
        break
        time.sleep(config['system']['delay'])