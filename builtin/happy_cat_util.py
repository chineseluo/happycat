import os
import re
import json
import functools
import warnings
import random
from loguru import logger
from config.user_agent import USER_AGENTS


class Util:
    @staticmethod
    def open_image(image_file):
        """
        用于打开二维码图片
        """
        if os.name == "nt":
            os.system('start ' + image_file)  # for Windows
        else:
            if os.uname()[0] == "Linux":
                if "deepin" in os.uname()[2]:
                    os.system("deepin-image-viewer " + image_file)  # for deepin
                else:
                    os.system("eog " + image_file)  # for Linux
            else:
                os.system("open " + image_file)  # for Mac

    @staticmethod
    def save_image(resp, image_file):
        """
        保存图片
        """
        with open(image_file, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024):
                f.write(chunk)

    @staticmethod
    def parse_json(s):
        begin = s.find('{')
        end = s.rfind('}') + 1
        return json.loads(s[begin:end])

    @staticmethod
    def get_tag_value(tag, key='', index=0):
        if key:
            value = tag[index].get(key)
        else:
            value = tag[index].text
        return value.strip(' \t\r\n')

    @staticmethod
    def parse_items_dict(d):
        result = ''
        for index, key in enumerate(d):
            if index < len(d) - 1:
                result = result + '{0} x {1}, '.format(key, d[key])
            else:
                result = result + '{0} x {1}'.format(key, d[key])
        return result

    @staticmethod
    def parse_sku_id(sku_ids):
        """将商品id字符串解析为字典

        商品id字符串采用英文逗号进行分割。
        可以在每个id后面用冒号加上数字，代表该商品的数量，如果不加数量则默认为1。

        例如：
        输入  -->  解析结果
        '123456' --> {'123456': '1'}
        '123456,123789' --> {'123456': '1', '123789': '1'}
        '123456:1,123789:3' --> {'123456': '1', '123789': '3'}
        '123456:2,123789' --> {'123456': '2', '123789': '1'}

        :param sku_ids: 商品id字符串
        :return: dict
        """
        if isinstance(sku_ids, dict):  # 防止重复解析
            return sku_ids

        sku_id_list = list(filter(bool, map(lambda x: x.strip(), sku_ids.split(','))))
        result = dict()
        for item in sku_id_list:
            if ':' in item:
                sku_id, count = map(lambda x: x.strip(), item.split(':'))
                result[sku_id] = count
            else:
                result[item] = '1'
        return result

    @staticmethod
    def parse_area_id(area):
        """解析地区id字符串：将分隔符替换为下划线 _
        :param area: 地区id字符串（使用 _ 或 - 进行分割），如 12_904_3375 或 12-904-3375
        :return: 解析后字符串
        """
        area_id_list = list(map(lambda x: x.strip(), re.split('_|-', area)))
        area_id_list.extend((4 - len(area_id_list)) * ['0'])
        return '_'.join(area_id_list)

    @staticmethod
    def split_area_id(area):
        """将地区id字符串按照下划线进行切割，构成数组。数组长度不满4位则用'0'进行填充。
        :param area: 地区id字符串（使用 _ 或 - 进行分割），如 12_904_3375 或 12-904-3375
        :return: list
        """
        area_id_list = list(map(lambda x: x.strip(), re.split('_|-', area)))
        area_id_list.extend((4 - len(area_id_list)) * ['0'])
        return area_id_list

    @staticmethod
    def deprecated(func):
        """This decorator is used to mark functions as deprecated.
        It will result in a warning being emitted when the function is used.
        """

        @functools.wraps(func)
        def new_func(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)  # turn off filter
            warnings.warn(
                "Call to deprecated function {}.".format(func.__name__),
                category=DeprecationWarning,
                stacklevel=2
            )
            warnings.simplefilter('default', DeprecationWarning)  # reset filter
            return func(*args, **kwargs)

        return new_func

    @staticmethod
    def check_login(func):
        """用户登陆态校验装饰器。若用户未登陆，则调用扫码登陆"""

        @functools.wraps(func)
        def new_func(self, *args, **kwargs):
            if not self.is_login:
                logger.info("{0} 需登陆后调用，开始扫码登陆".format(func.__name__))
                self.login_by_QRcode()
            return func(self, *args, **kwargs)

        return new_func

    @staticmethod
    def get_random_useragent():
        """生成随机的UserAgent
        :return: UserAgent字符串
        """
        return random.choice(USER_AGENTS)
