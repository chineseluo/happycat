# 用于获取秒杀商品的必须信息
import requests
import re
import time
import random
from config import global_config
from loguru import logger
from builtin.happy_cat_util import Util


class SearchGoods:
    def __init__(self):
        self.default_user_agent = global_config.getRaw('config', 'DEFAULT_USER_AGENT')
        self.headers = {'User-Agent': self.default_user_agent}
        # 购物车
        self.shopping_car = dict()
        # 商家ID
        self.business_id = dict()
        self.timeout = 1

    def get_item_detail_page(self, sku_id):
        """访问商品详情页
        :param sku_id: 商品id
        :return: 响应
        """
        url = 'https://item.jd.com/{}.html'.format(sku_id)
        page = requests.get(url=url, headers=self.headers)
        return page

    def get_single_item_stock(self, sku_id, num, area):
        """获取单个商品库存状态
        :param sku_id: 商品id
        :param num: 商品数量
        :param area: 地区id
        :return: 商品是否有货 True/False
        """
        area_id = Util.parse_area_id(area)

        cat = self.shopping_car.get(sku_id)
        vender_id = self.business_id.get(sku_id)
        if not cat:
            page = self.get_item_detail_page(sku_id)
            match = re.search(r'cat: \[(.*?)\]', page.text)
            cat = match.group(1)
            self.shopping_car[sku_id] = cat

            match = re.search(r'venderId:(\d*?),', page.text)
            vender_id = match.group(1)
            self.business_id[sku_id] = vender_id

        url = 'https://c0.3.cn/stock'
        payload = {
            'skuId': sku_id,
            'buyNum': num,
            'area': area_id,
            'ch': 1,
            '_': str(int(time.time() * 1000)),
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'extraParam': '{"originid":"1"}',  # get error stock state without this param
            'cat': cat,  # get 403 Forbidden without this param (obtained from the detail page)
            'venderId': vender_id  # return seller information with this param (can't be ignored)
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://item.jd.com/{}.html'.format(sku_id),
        }

        resp_text = ''
        try:
            resp_text = requests.get(url=url, params=payload, headers=headers, timeout=self.timeout).text
            resp_json = Util.parse_json(resp_text)
            logger.info(resp_json)
            stock_info = resp_json.get('stock')
            sku_state = stock_info.get('skuState')  # 商品是否上架
            stock_state = stock_info.get('StockState')  # 商品库存状态：33 -- 现货  0,34 -- 无货  36 -- 采购中  40 -- 可配货
            return sku_state == 1 and stock_state in (33, 40)
        except requests.exceptions.Timeout:
            logger.error(f'快乐喵查询:【{sku_id}】 %s 库存信息超时【{self.timeout}】')
            return False
        except requests.exceptions.RequestException as request_exception:
            logger.error(f'快乐喵查询【{sku_id}库存信息发生网络请求异常：【{request_exception}】')
            return False
        except Exception as e:
            logger.error(f'快乐喵查询【{sku_id}】库存信息发生异常, 响应信息: 【{resp_text}】, 错误信息: 【{e}】')
            return False


if __name__ == '__main__':
    sg = SearchGoods()
    sg.get_item_detail_page("69908843806")
    res = sg.get_single_item_stock("100004293861",1,"22_1930_49324_49398")
    print(res)
