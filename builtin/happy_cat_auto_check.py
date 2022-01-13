import binascii
import base64
import hashlib
import datetime
from typing import Text, Dict, ByteString
from loguru import logger


# 用来发放license进行加密解密，同步url进行数据校验，初始化时候，即校验快乐喵是否过期
class AuthBuiltInCheck:

    @staticmethod
    def add_crt(user_info: Dict) -> ByteString:
        """
        生成加密happy_cat license内容
        """
        add_first_pwd = binascii.b2a_hex(Text(user_info).encode("utf-8"))
        add_second_pwd = base64.b32encode(add_first_pwd)
        return add_second_pwd

    @staticmethod
    def decrypt_crt(crt_content: ByteString) -> Text:
        """
        解密happy_cat license内容
        """
        decrypt_first_pwd = base64.b32decode(crt_content)
        decrypt_second_pwd = binascii.a2b_hex(decrypt_first_pwd).decode("utf-8")
        return decrypt_second_pwd


licence_dict = {
    "start_time": Text(datetime.datetime.now()),
    "end_time": Text(datetime.datetime.now()),
    "username": "happy_cat"
}
