# -*- coding:utf-8 -*-
import time
from datetime import datetime

from loguru import logger


# 定时器，时间到达，开始运行任务
class Timer(object):

    def __init__(self, buy_time, sleep_interval=0.2):

        # '2018-09-28 22:45:50.000'
        self.buy_time = datetime.strptime(buy_time, "%Y-%m-%d %H:%M:%S.%f")
        self.sleep_interval = sleep_interval

    def start(self):
        logger.info(f'快乐喵闹钟提醒，计划捕猎时间为：【{self.buy_time}】')
        now_time = datetime.now
        while True:
            if now_time() >= self.buy_time:
                logger.info('快乐喵提示，时间到了，快乐喵开始捕食！！！')
                break
            else:
                time.sleep(self.sleep_interval)
