# 用于获取秒杀商品的必须信息
import requests
import re
import time
import random
from config import global_config
from loguru import logger
from builtin.happy_cat_util import Util
from typing import Text


class SearchGoods:
    def __init__(self, session):
        self.default_user_agent = global_config.getRaw('config', 'DEFAULT_USER_AGENT')
        self.headers = {'User-Agent': self.default_user_agent}
        # 购物车
        self.shopping_car = dict()
        # 商家ID
        self.business_id = dict()
        self.timeout = 1
        self.session = session

    def get_item_detail_page(self, sku_id):
        """访问商品详情页
        :param sku_id: 商品id
        :return: 响应
        """
        url = 'https://item.jd.com/{}.html'.format(sku_id)
        page = requests.get(url=url, headers=self.headers)
        return page

    def get_single_item_stock(self, sku_id, num, area) -> bool:
        """获取单个商品库存状态判断是否有货
        :param sku_id: 商品id
        :param num: 商品数量
        :param area: 地区id
        :return: 商品是否有货 True/False
        """
        area_id = Util.parse_area_id(area)
        logger.info(self.shopping_car)
        cat = self.shopping_car.get(sku_id)
        logger.info(cat)

        vender_id = self.business_id.get(sku_id)
        if not cat:
            page = self.get_item_detail_page(sku_id)
            match = re.search(r'cat: \[(.*?)\]', page.text)
            logger.info(match)
            cat = match.group(1)
            self.shopping_car[sku_id] = cat

            match = re.search(r'venderId:(\d*?),', page.text)
            vender_id = match.group(1)
            logger.info(vender_id)
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

    def get_multi_item_stock_new(self, sku_ids, area):
        """获取多个商品库存状态（新）
        当所有商品都有货，返回True；否则，返回False。
        :param sku_ids: 多个商品的id。可以传入中间用英文逗号的分割字符串，如"123,456"
        :param area: 地区id
        :return: 多个商品是否同时有货 True/False
        """
        items_dict = Util.parse_sku_id(sku_ids=sku_ids)
        area_id = Util.parse_area_id(area=area)

        url = 'https://c0.3.cn/stocks'
        payload = {
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'type': 'getstocks',
            'skuIds': ','.join(items_dict.keys()),
            'area': area_id,
            '_': str(int(time.time() * 1000))
        }
        headers = {
            'User-Agent': self.default_user_agent
        }

        resp_text = ''
        try:
            resp_text = requests.get(url=url, params=payload, headers=headers, timeout=self.timeout).text
            stock = True
            for sku_id, info in Util.parse_json(resp_text).items():
                sku_state = info.get('skuState')  # 商品是否上架
                stock_state = info.get('StockState')  # 商品库存状态
                if sku_state == 1 and stock_state in (33, 40):
                    continue
                else:
                    stock = False
                    break
            return stock
        except requests.exceptions.Timeout:
            logger.error('查询 %s 库存信息超时(%ss)', list(items_dict.keys()), self.timeout)
            return False
        except requests.exceptions.RequestException as request_exception:
            logger.error('查询 %s 库存信息发生网络请求异常：%s', list(items_dict.keys()), request_exception)
            return False
        except Exception as e:
            logger.error('查询 %s 库存信息发生异常, resp: %s, exception: %s', list(items_dict.keys()), resp_text, e)
            return False

    def if_goods_is_removed(self, sku_id) -> bool:
        """判断商品是否下架
        :param sku_id: 商品id
        :return: 商品是否下架 True/False
        """
        detail_page = self.get_item_detail_page(sku_id=sku_id)
        if '该商品已下柜' in detail_page.text:
            logger.warning(f'快乐喵警告：该商品已下架，小猫的快乐丢失了，换一个其他的商品吧')
            return True
        else:
            logger.info(f'快乐喵提示：商品【{sku_id}】未下架，可以进行操作哦')
            return False

    def if_goods_can_be_ordered(self, sku_ids, area):
        """判断商品是否能下单
        :param sku_ids: 商品id，多个商品id中间使用英文逗号进行分割
        :param area: 地址id
        :return: 商品是否能下单 True/False
        """
        items_dict = Util.parse_sku_id(sku_ids=sku_ids)
        area_id = Util.parse_area_id(area)

        # 判断商品是否能下单
        if len(items_dict) > 1:
            return self.get_multi_item_stock_new(sku_ids=items_dict, area=area_id)

        sku_id, count = list(items_dict.items())[0]
        return self.get_single_item_stock(sku_id=sku_id, num=count, area=area_id)

    def get_item_price(self, sku_id) -> Text:
        """获取商品价格
        :param sku_id: 商品id
        :return: 价格
        """
        url = 'http://p.3.cn/prices/mgets'
        payload = {
            'type': 1,
            'pduid': int(time.time() * 1000),
            'skuIds': 'J_' + sku_id,
        }
        resp = self.session.get(url=url, params=payload)
        return Util.parse_json(resp.text).get('p')


if __name__ == '__main__':
    from jd_spider_requests import JdSeckill
    jd =JdSeckill()
    sg = SearchGoods(jd.session)
    res4 = sg.if_goods_can_be_ordered("69908843806,100004293861", "22_1930_49324_49398")
    res5 = sg.get_item_price("100004293861")
