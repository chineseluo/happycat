import random
import time
import json
from bs4 import BeautifulSoup
from builtin.happy_cat_util import Util
from loguru import logger
from config import global_config
from builtin.happy_cat_exception import HappyCatAddGoodsToShoppingCarException


class ShoppingCar:
    def __init__(self, session):
        self.default_user_agent = global_config.getRaw('config', 'DEFAULT_USER_AGENT')
        self.eid = global_config.getRaw('config', 'eid')
        self.fp = global_config.getRaw('config', 'fp')
        self.track_id = global_config.getRaw('config', 'track_id')
        self.risk_control = "VIM1504:4"
        self.session = session

    def add_item_to_cart(self, sku_ids):
        """添加商品到购物车

        重要：
        1.商品添加到购物车后将会自动被勾选✓中。
        2.在提交订单时会对勾选的商品进行结算。
        3.部分商品（如预售、下架等）无法添加到购物车

        京东购物车可容纳的最大商品种数约为118-120种，超过数量会加入购物车失败。

        :param sku_ids: 商品id，格式："123" 或 "123,456" 或 "123:1,456:2"。若不配置数量，默认为1个。
        :return:
        """
        url = 'https://cart.jd.com/gate.action'
        headers = {
            'User-Agent': self.default_user_agent,
        }

        for sku_id, count in Util.parse_sku_id(sku_ids=sku_ids).items():
            payload = {
                'pid': sku_id,
                'pcount': count,
                'ptype': 1,
            }
            resp = self.session.get(url=url, params=payload, headers=headers)
            if 'https://cart.jd.com/cart.action' in resp.url:  # 套装商品加入购物车后直接跳转到购物车页面
                result = True
            else:  # 普通商品成功加入购物车后会跳转到提示 "商品已成功加入购物车！" 页面
                soup = BeautifulSoup(resp.text, "html.parser")
                result = bool(soup.select('h3.ftx-02'))  # [<h3 class="ftx-02">商品已成功加入购物车！</h3>]

            if result:
                logger.info(f'快乐喵已成功将商品【{sku_id}】数量【{count}】加入购物车，喵喵喵')
            else:
                logger.error(f'快乐喵添加商品【{sku_id}】失败！！！')
                raise HappyCatAddGoodsToShoppingCarException(f'快乐喵添加商品【{sku_id}】失败！！！', )

    def clear_cart(self):
        """清空购物车

        包括两个请求：
        1.选中购物车中所有的商品
        2.批量删除

        :return: 清空购物车结果 True/False
        """
        # 1.select all items  2.batch remove items
        select_url = 'https://cart.jd.com/selectAllItem.action'
        remove_url = 'https://cart.jd.com/batchRemoveSkusFromCart.action'
        data = {
            't': 0,
            'outSkus': '',
            'random': random.random(),
        }
        try:
            select_resp = self.session.post(url=select_url, data=data)
            remove_resp = self.session.post(url=remove_url, data=data)
            if (not Util.response_status(select_resp)) or (not Util.response_status(remove_resp)):
                logger.error('快乐喵购物车清空失败!!!')
                return False
            logger.info('快乐喵购物车清空成功，喵喵喵')
            return True
        except Exception as e:
            logger.info(f'快乐喵购物车清空出现异常，异常原因【{e}】')
            return False

    def get_cart_detail(self):
        """
        Todo 接口不通
        获取购物车商品详情
        :return: 购物车商品信息 dict
        """
        url = 'https://cart.jd.com/cart.action'
        resp = self.session.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        logger.info(resp.text)
        cart_detail = dict()
        for item in soup.find_all(class_='item-item'):
            try:
                sku_id = item['skuid']  # 商品id
                # 例如：['increment', '8888', '100001071956', '1', '13', '0', '50067652554']
                # ['increment', '8888', '100002404322', '2', '1', '0']
                item_attr_list = item.find(class_='increment')['id'].split('_')
                p_type = item_attr_list[4]
                promo_id = target_id = item_attr_list[-1] if len(item_attr_list) == 7 else 0

                cart_detail[sku_id] = {
                    'name': Util.get_tag_value(item.select('div.p-name a')),  # 商品名称
                    'verder_id': item['venderid'],  # 商家id
                    'count': int(item['num']),  # 数量
                    'unit_price': Util.get_tag_value(item.select('div.p-price strong'))[1:],  # 单价
                    'total_price': Util.get_tag_value(item.select('div.p-sum strong'))[1:],  # 总价
                    'is_selected': 'item-selected' in item['class'],  # 商品是否被勾选
                    'p_type': p_type,
                    'target_id': target_id,
                    'promo_id': promo_id
                }
            except Exception as e:
                logger.error("某商品在购物车中的信息无法解析，报错信息: %s，该商品自动忽略。 %s", e, item)

        logger.info(f'购物车信息：【{cart_detail}】')
        return cart_detail

    def submit_order_with_retry(self, retry=3, interval=4):
        """提交订单，并且带有重试功能
        :param retry: 重试次数
        :param interval: 重试间隔
        :return: 订单提交结果 True/False
        """
        for i in range(1, retry + 1):
            logger.info('第[%s/%s]次尝试提交订单', i, retry)
            self.get_checkout_page_detail()
            if self.submit_order():
                logger.info('第%s次提交订单成功', i)
                return True
            else:
                if i < retry:
                    logger.info('第%s次提交失败，%ss后重试', i, interval)
                    time.sleep(interval)
        else:
            logger.info('重试提交%s次结束', retry)
            return False

    def _save_invoice(self):
        """下单第三方商品时如果未设置发票，将从电子发票切换为普通发票

        http://jos.jd.com/api/complexTemplate.htm?webPamer=invoice&groupName=%E5%BC%80%E6%99%AE%E5%8B%92%E5%85%A5%E9%A9%BB%E6%A8%A1%E5%BC%8FAPI&id=566&restName=jd.kepler.trade.submit&isMulti=true

        :return:
        """
        url = 'https://trade.jd.com/shopping/dynamic/invoice/saveInvoice.action'
        data = {
            "invoiceParam.selectedInvoiceType": 1,
            "invoiceParam.companyName": "个人",
            "invoiceParam.invoicePutType": 0,
            "invoiceParam.selectInvoiceTitle": 4,
            "invoiceParam.selectBookInvoiceContent": "",
            "invoiceParam.selectNormalInvoiceContent": 1,
            "invoiceParam.vatCompanyName": "",
            "invoiceParam.code": "",
            "invoiceParam.regAddr": "",
            "invoiceParam.regPhone": "",
            "invoiceParam.regBank": "",
            "invoiceParam.regBankAccount": "",
            "invoiceParam.hasCommon": "true",
            "invoiceParam.hasBook": "false",
            "invoiceParam.consigneeName": "",
            "invoiceParam.consigneePhone": "",
            "invoiceParam.consigneeAddress": "",
            "invoiceParam.consigneeProvince": "请选择：",
            "invoiceParam.consigneeProvinceId": "NaN",
            "invoiceParam.consigneeCity": "请选择",
            "invoiceParam.consigneeCityId": "NaN",
            "invoiceParam.consigneeCounty": "请选择",
            "invoiceParam.consigneeCountyId": "NaN",
            "invoiceParam.consigneeTown": "请选择",
            "invoiceParam.consigneeTownId": 0,
            "invoiceParam.sendSeparate": "false",
            "invoiceParam.usualInvoiceId": "",
            "invoiceParam.selectElectroTitle": 4,
            "invoiceParam.electroCompanyName": "undefined",
            "invoiceParam.electroInvoiceEmail": "",
            "invoiceParam.electroInvoicePhone": "",
            "invokeInvoiceBasicService": "true",
            "invoice_ceshi1": "",
            "invoiceParam.showInvoiceSeparate": "false",
            "invoiceParam.invoiceSeparateSwitch": 1,
            "invoiceParam.invoiceCode": "",
            "invoiceParam.saveInvoiceFlag": 1
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://trade.jd.com/shopping/dynamic/invoice/saveInvoice.action',
        }
        self.session.post(url=url, data=data, headers=headers)

    def submit_order(self):
        """提交订单

        重要：
        1.该方法只适用于普通商品的提交订单（即可以加入购物车，然后结算提交订单的商品）
        2.提交订单时，会对购物车中勾选✓的商品进行结算（如果勾选了多个商品，将会提交成一个订单）

        :return: True/False 订单提交结果
        """
        url = 'https://trade.jd.com/shopping/order/submitOrder.action'
        # js function of submit order is included in https://trade.jd.com/shopping/misc/js/order.js?r=2018070403091

        data = {
            'overseaPurchaseCookies': '',
            'vendorRemarks': '[]',
            'submitOrderParam.sopNotPutInvoice': 'false',
            'submitOrderParam.trackID': 'TestTrackId',
            'submitOrderParam.ignorePriceChange': '0',
            'submitOrderParam.btSupport': '0',
            # 'riskControl': self.risk_control,
            'riskControl': None,
            'submitOrderParam.isBestCoupon': 1,
            'submitOrderParam.jxj': 1,
            'submitOrderParam.TrackID': self.track_id,  # Todo: need to get trackId
            'submitOrderParam.eid': self.eid,
            'submitOrderParam.fp': self.fp,
            'submitOrderParam.needCheck': 1,
        }

        logger.info(data)
        # add payment password when necessary
        payment_pwd = global_config.get('account', 'payment_pwd')
        if payment_pwd:
            data['submitOrderParam.payPassword'] = Util.encrypt_payment_pwd(payment_pwd)

        headers = {
            'User-Agent': self.default_user_agent,
            'Host': 'trade.jd.com',
            'Referer': 'http://trade.jd.com/shopping/order/getOrderInfo.action',
        }

        try:
            resp = self.session.post(url=url, data=data, headers=headers)
            logger.info(resp.text)
            resp_json = json.loads(resp.text)
            logger.info(resp_json)

            # 返回信息示例：
            # 下单失败
            # {'overSea': False, 'orderXml': None, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': False, 'resultCode': 60123, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': '请输入支付密码！'}
            # {'overSea': False, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'orderXml': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': False, 'resultCode': 60017, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': '您多次提交过快，请稍后再试'}
            # {'overSea': False, 'orderXml': None, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': False, 'resultCode': 60077, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': '获取用户订单信息失败'}
            # {"cartXml":null,"noStockSkuIds":"xxx","reqInfo":null,"hasJxj":false,"addedServiceList":null,"overSea":false,"orderXml":null,"sign":null,"pin":"xxx","needCheckCode":false,"success":false,"resultCode":600157,"orderId":0,"submitSkuNum":0,"deductMoneyFlag":0,"goJumpOrderCenter":false,"payInfo":null,"scaleSkuInfoListVO":null,"purchaseSkuInfoListVO":null,"noSupportHomeServiceSkuList":null,"msgMobile":null,"addressVO":{"pin":"xxx","areaName":"","provinceId":xx,"cityId":xx,"countyId":xx,"townId":xx,"paymentId":0,"selected":false,"addressDetail":"xx","mobile":"xx","idCard":"","phone":null,"email":null,"selfPickMobile":null,"selfPickPhone":null,"provinceName":null,"cityName":null,"countyName":null,"townName":null,"giftSenderConsigneeName":null,"giftSenderConsigneeMobile":null,"gcLat":0.0,"gcLng":0.0,"coord_type":0,"longitude":0.0,"latitude":0.0,"selfPickOptimize":0,"consigneeId":0,"selectedAddressType":0,"siteType":0,"helpMessage":null,"tipInfo":null,"cabinetAvailable":true,"limitKeyword":0,"specialRemark":null,"siteProvinceId":0,"siteCityId":0,"siteCountyId":0,"siteTownId":0,"skuSupported":false,"addressSupported":0,"isCod":0,"consigneeName":null,"pickVOname":null,"shipmentType":0,"retTag":0,"tagSource":0,"userDefinedTag":null,"newProvinceId":0,"newCityId":0,"newCountyId":0,"newTownId":0,"newProvinceName":null,"newCityName":null,"newCountyName":null,"newTownName":null,"checkLevel":0,"optimizePickID":0,"pickType":0,"dataSign":0,"overseas":0,"areaCode":null,"nameCode":null,"appSelfPickAddress":0,"associatePickId":0,"associateAddressId":0,"appId":null,"encryptText":null,"certNum":null,"used":false,"oldAddress":false,"mapping":false,"addressType":0,"fullAddress":"xxxx","postCode":null,"addressDefault":false,"addressName":null,"selfPickAddressShuntFlag":0,"pickId":0,"pickName":null,"pickVOselected":false,"mapUrl":null,"branchId":0,"canSelected":false,"address":null,"name":"xxx","message":null,"id":0},"msgUuid":null,"message":"xxxxxx商品无货"}
            # {'orderXml': None, 'overSea': False, 'noStockSkuIds': 'xxx', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'cartXml': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': False, 'resultCode': 600158, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': {'oldAddress': False, 'mapping': False, 'pin': 'xxx', 'areaName': '', 'provinceId': xx, 'cityId': xx, 'countyId': xx, 'townId': xx, 'paymentId': 0, 'selected': False, 'addressDetail': 'xxxx', 'mobile': 'xxxx', 'idCard': '', 'phone': None, 'email': None, 'selfPickMobile': None, 'selfPickPhone': None, 'provinceName': None, 'cityName': None, 'countyName': None, 'townName': None, 'giftSenderConsigneeName': None, 'giftSenderConsigneeMobile': None, 'gcLat': 0.0, 'gcLng': 0.0, 'coord_type': 0, 'longitude': 0.0, 'latitude': 0.0, 'selfPickOptimize': 0, 'consigneeId': 0, 'selectedAddressType': 0, 'newCityName': None, 'newCountyName': None, 'newTownName': None, 'checkLevel': 0, 'optimizePickID': 0, 'pickType': 0, 'dataSign': 0, 'overseas': 0, 'areaCode': None, 'nameCode': None, 'appSelfPickAddress': 0, 'associatePickId': 0, 'associateAddressId': 0, 'appId': None, 'encryptText': None, 'certNum': None, 'addressType': 0, 'fullAddress': 'xxxx', 'postCode': None, 'addressDefault': False, 'addressName': None, 'selfPickAddressShuntFlag': 0, 'pickId': 0, 'pickName': None, 'pickVOselected': False, 'mapUrl': None, 'branchId': 0, 'canSelected': False, 'siteType': 0, 'helpMessage': None, 'tipInfo': None, 'cabinetAvailable': True, 'limitKeyword': 0, 'specialRemark': None, 'siteProvinceId': 0, 'siteCityId': 0, 'siteCountyId': 0, 'siteTownId': 0, 'skuSupported': False, 'addressSupported': 0, 'isCod': 0, 'consigneeName': None, 'pickVOname': None, 'shipmentType': 0, 'retTag': 0, 'tagSource': 0, 'userDefinedTag': None, 'newProvinceId': 0, 'newCityId': 0, 'newCountyId': 0, 'newTownId': 0, 'newProvinceName': None, 'used': False, 'address': None, 'name': 'xx', 'message': None, 'id': 0}, 'msgUuid': None, 'message': 'xxxxxx商品无货'}
            # 下单成功
            # {'overSea': False, 'orderXml': None, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': True, 'resultCode': 0, 'orderId': 8740xxxxx, 'submitSkuNum': 1, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': None}

            if resp_json.get('success'):
                order_id = resp_json.get('orderId')
                logger.info('订单提交成功! 订单号：%s', order_id)
                # if self.send_message:
                #     self.messenger.send(text='jd-assistant 订单提交成功', desp='订单号：%s' % order_id)
                # return True
            else:
                message, result_code = resp_json.get('message'), resp_json.get('resultCode')
                if result_code == 0:
                    self._save_invoice()
                    message = message + '(下单商品可能为第三方商品，将切换为普通发票进行尝试)'
                elif result_code == 60077:
                    message = message + '(可能是购物车为空 或 未勾选购物车中商品)'
                elif result_code == 60123:
                    message = message + '(需要在config.ini文件中配置支付密码)'
                logger.info('订单提交失败, 错误码：%s, 返回信息：%s', result_code, message)
                logger.info(resp_json)
                return False
        except Exception as e:
            logger.error(e)
            return False

    def get_checkout_page_detail(self):
        """获取订单结算页面信息

        该方法会返回订单结算页面的详细信息：商品名称、价格、数量、库存状态等。

        :return: 结算信息 dict
        """
        url = 'http://trade.jd.com/shopping/order/getOrderInfo.action'
        # url = 'https://cart.jd.com/gotoOrder.action'
        payload = {
            'rid': str(int(time.time() * 1000)),
        }
        try:
            resp = self.session.get(url=url, params=payload)
            if not Util.response_status(resp):
                logger.error('获取订单结算页信息失败')
                return

            soup = BeautifulSoup(resp.text, "html.parser")
            self.risk_control = Util.get_tag_value(soup.select('input#riskControl'), 'value')

            order_detail = {
                'address': soup.find('span', id='sendAddr').text[5:],  # remove '寄送至： ' from the begin
                'receiver': soup.find('span', id='sendMobile').text[4:],  # remove '收件人:' from the begin
                'total_price': soup.find('span', id='sumPayPriceId').text[1:],  # remove '￥' from the begin
                'items': []
            }
            logger.info(order_detail)
            # TODO: 这里可能会产生解析问题，待修复
            # for item in soup.select('div.goods-list div.goods-items'):
            #     div_tag = item.select('div.p-price')[0]
            #     order_detail.get('items').append({
            #         'name': get_tag_value(item.select('div.p-name a')),
            #         'price': get_tag_value(div_tag.select('strong.jd-price'))[2:],  # remove '￥ ' from the begin
            #         'num': get_tag_value(div_tag.select('span.p-num'))[1:],  # remove 'x' from the begin
            #         'state': get_tag_value(div_tag.select('span.p-state'))  # in stock or out of stock
            #     })

            logger.info("下单信息：%s", order_detail)
            return order_detail
        except Exception as e:
            logger.error('订单结算页面数据解析异常（可以忽略），报错信息：%s', e)


if __name__ == '__main__':
    from jd_spider_requests import JdSeckill

    jd = JdSeckill()
    sc = ShoppingCar(jd.session)
    # sc.add_item_to_cart("69908843806,100004293861")
    # sc.get_cart_detail()
    sc.submit_order()