import sys
from jd_spider_requests import JdSeckill
from loguru import logger

if __name__ == '__main__':
    a = """
    快乐喵工具                                                                           
    功能列表：                                                                                
    1.预约商品
    2.秒杀抢购商品
 
    """
    logger.info(a)

    jd_seckill = JdSeckill()
    choice_function = input('请选择:')
    if choice_function == '1':
        jd_seckill.reserve()
    elif choice_function == '2':
        jd_seckill.seckill_by_proc_pool()
    else:
        print('没有此功能')
        sys.exit(1)

