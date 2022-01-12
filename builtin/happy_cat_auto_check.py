import binascii
import base64
import hashlib
import datetime
from typing import Text
from loguru import logger
# 用来发放license进行加密解密，同步url进行数据校验，初始化时候，即校验快乐喵是否过期
# 方法中不传参数则是以默认的utf-8编码进行转换
licence_dict = {
    "start_time": Text(datetime.datetime.now()),
    "end_time": Text(datetime.datetime.now()),
    "username": "happy_cat"
}

add_first_pwd = binascii.b2a_hex(Text(licence_dict).encode("utf-8"))
logger.info(f'开始第一层加密：{add_first_pwd}')
add_second_pwd = base64.b32encode(add_first_pwd)
logger.info(f"开始第二层加密：{add_second_pwd}")
decrypt_first_pwd = base64.b32decode(add_second_pwd)
logger.info(f'开始第一层解密：{decrypt_first_pwd}')
decrypt_second_pwd = binascii.a2b_hex(add_first_pwd).decode("utf-8")
logger.info(f'开始第二层解密：{decrypt_second_pwd}')

