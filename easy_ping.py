from gevent import monkey
monkey.patch_all()

import os
import re
import subprocess
import time
import yaml
import gevent
import logging
import requests
from influx import InfluxLogger
from utils import (
    retry
)
from gevent.pool import Pool
from gevent.subprocess import Popen, PIPE
from http import HTTPStatus

logger = logging.Logger(__name__)

FETCH_GET = 'get'
FETCH_POST = 'post'

class BadFetchMethodExc(Exception):
    pass

class BadResponseStatusCode(Exception):
    pass

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

def make_fetch(url, method=FETCH_GET, params=None):
    print('Fetch:', url, method, params)
    try:
        if method == FETCH_GET:
            req = requests.get(
                url=url,
                params=params,
            )

        elif method == FETCH_POST:
            req = requests.post(
                url=url,
                data=params
            )
        else:
            raise BadFetchMethodExc
    except Exception as ex:
        logger.exception(ex)
        raise ex
    
    if req.status_code != HTTPStatus.OK:
        raise BadResponseStatusCode(req.status_code)
    
    return req.text
    

def fetch_test(order_id, url, check_stamp_text):
    try:
        req = requests.get(url)
    except Exception as ex:
        logger.exception(ex)
        logger.error('Error Fetch:{site}\tOrder:{order_id}'.format(
            site=url,
            order_id=order_id,
        ))
        return
    
    if req.status_code == HTTPStatus.OK and req.text[0:len(check_stamp_text)] == check_stamp_text:
        return None
    
    logger.error('Error Fetch:{site}\tOrder:{order_id}\tHTTP_STATUS:{status}'.format(
        site=url,
        order_id=order_id,
        status=req.status_code,
    ))


def run_server(config):
    ping_tasks = config['monitor'].get('ping')
    fetch_tasks = config['monitor'].get('fetch')
    workers = []

    if ping_tasks:
        ping_times = config['monitor'].get('ping_times', 5)
        workers = [gevent.spawn(make_ping, target_name, addr, ping_times) for target_name, addr in ping_tasks.items()]

    if fetch_tasks:
        fetch_work_api = fetch_tasks.get('fetch_work_api')
        fetch_work_key = fetch_tasks.get('fetch_work_key')
        fetch_check_stamp = fetch_tasks.get('fetch_check_stamp')
        if not fetch_work_api or not fetch_work_key:
            logger.info('NO FETCH TASK CONFIGURED')
        else:
            data = make_fetch(fetch_work_api, FETCH_GET, {'key': fetch_work_key})
            import json
            try:
                result = json.loads(data)
            except Exception as ex:
                logger.exception(ex)

            for i, fetch_task in enumerate(result['list']):
                workers = [gevent.spawn(
                    fetch_test,
                    fetch_task['order_id'],
                    'http://' + fetch_task['order_url'],
                    fetch_tasks.get('fetch_check_stamp')
                )]

    if workers:
        gevent.joinall(workers)

if __name__ == "__main__":
    while(1):
        config = read_config()
        il = InfluxLogger(config)
        run_server(config)

        break
        time.sleep(config['system']['delay'])
