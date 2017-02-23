import socket
import logging
from influxdb import InfluxDBClient

logger = logging.Logger(__name__)

class InfluxLogger:
    def __init__(self, config):
        self.client = InfluxDBClient(host=config['influx_db']['host'],
                                port=config['influx_db']['port'],
                                username=config['influx_db']['user'],
                                password=config['influx_db']['password'],
                                database=config['influx_db']['database'])
        self.config = config

    def log(self, module_name, target, kwargs):
        json_body = [
            {
                "measurement": module_name,
                "tags": {
                    "host": socket.gethostname(),
                    "region": self.config['system']['region'],
                    "target": target
                },
                "fields": kwargs
            }
        ]

        if not self.client.write_points(json_body):
            logger.error('influx logging failed')
            logger.info(json_body)