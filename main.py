import sys
from jd_spider_requests import JdSeckill
from loguru import logger
from job_center.login import Login
if __name__ == '__main__':
    a = """
    快乐喵工具                                                                           
    功能列表：                                                                                
    1.预约商品
    2.秒杀抢购商品
 
    """
    logger.info(a)
    login_client = Login()
    login_client.login_by_QRcode()


