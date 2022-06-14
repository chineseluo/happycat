import os
import time
import pickle
import sys
import json
import random
import requests
from loguru import logger
from config import global_config
from builtin.happy_cat_util import Util, DEFAULT_USER_AGENT
from builtin.happy_cat_exception import *
from bs4 import BeautifulSoup


class Login:
    def __init__(self):
        self.session = requests.session()
        self.nick_name = ""
        self.eid = ""
        self.fp = ""
        self.is_login = False
        self.default_user_agent = DEFAULT_USER_AGENT#Util.get_random_useragent()
        self.headers = {'User-Agent': self.default_user_agent}


    def _save_cookies(self):
        """
        保存cookie
        """
        cookies_file = './cookies/{0}.cookies'.format(self.nick_name)
        directory = os.path.dirname(cookies_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(cookies_file, 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def _load_cookies(self):
        """
        加载cookie
        """
        cookies_file = ''
        for name in os.listdir('./cookies'):
            if name.endswith('.cookies'):
                cookies_file = './cookies/{0}'.format(name)
                break
        with open(cookies_file, 'rb') as f:
            local_cookies = pickle.load(f)
        self.session.cookies.update(local_cookies)
        self.is_login = self._validate_cookies()

    def _validate_cookies(self):
        for flag in range(1, 4):
            try:
                targetURL = 'https://order.jd.com/center/list.action'
                payload = {
                    'rid': str(int(time.time() * 1000)),
                }
                resp = self.session.get(url=targetURL, params=payload, allow_redirects=False)
                logger.info(f'快乐喵工具：尝试第{flag}次登录')
                logger.info(f'快乐喵工具：开始登录URL：{resp.url}')
                if resp.status_code == requests.codes.OK:
                    logger.info('快乐喵工具登录：[成功]')
                    logger.info('登录用户:{}'.format(self.get_username()))
                    return True
                else:
                    logger.warning('快乐喵工具登录：[失败]')
                    logger.warning('快乐喵工具提示：请重新检查cookie')
                    if flag == 3:
                        raise HappyCatLoginException(f'快乐喵工具登录失败，请重新核实cookie，或呼叫外援提供帮助！！')
                    time.sleep(1)
            except HappyCatLoginException as e:
                logger.error(f'快乐喵工具：第{flag}次重试登录失败，请重新核实cookie，或呼叫外援提供帮助！！！')
                logger.error("快乐喵工具：异常退出！！！")
        sys.exit(1)

    def wati_some_time(self):
        time.sleep(random.randint(100, 300) / 1000)

    def get_username(self):
        """获取用户信息"""
        url = 'https://passport.jd.com/user/petName/getUserInfoForMiniJd.action'
        payload = {
            'callback': 'jQuery'.format(random.randint(1000000, 9999999)),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://order.jd.com/center/list.action',
        }

        resp = self.session.get(url=url, params=payload, headers=headers)

        try_count = 5
        while not resp.text.startswith("jQuery"):
            try_count = try_count - 1
            if try_count > 0:
                resp = self.session.get(url=url, params=payload, headers=headers)
            else:
                break
            self.wati_some_time()
        # 响应中包含了许多用户信息，现在在其中返回昵称
        # jQuery2381773({"imgUrl":"//storage.360buyimg.com/i.imageUpload/xxx.jpg","lastLoginTime":"","nickName":"xxx","plusStatus":"0","realName":"xxx","userLevel":x,"userScoreVO":{"accountScore":xx,"activityScore":xx,"consumptionScore":xxxxx,"default":false,"financeScore":xxx,"pin":"xxx","riskScore":x,"totalScore":xxxxx}})
        nick_name = Util.parse_json(resp.text).get('nickName')
        logger.info(f'快乐喵获取用户名：{nick_name}')
        return nick_name

    def _get_auth_code(self, uuid):
        image_file = os.path.join(os.getcwd(), 'jd_authcode.jpg')

        url = 'https://authcode.jd.com/verify/image'
        payload = {
            'a': 1,
            'acid': uuid,
            'uid': uuid,
            'yys': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://passport.jd.com/uc/login',
        }
        resp = self.session.get(url, params=payload, headers=headers)

        if not Util.response_status(resp):
            logger.error('获取验证码失败')
            return ''

        Util.save_image(resp, image_file)
        Util.open_image(image_file)
        return input('验证码:')

    def _get_login_page(self):
        url = "https://passport.jd.com/new/login.aspx"
        page = self.session.get(url, headers=self.headers)
        return page

    def _get_login_data(self):
        page = self._get_login_page()
        soup = BeautifulSoup(page.text, "html.parser")
        input_list = soup.select('.form input')

        # eid & fp are generated by local javascript code according to browser environment
        return {
            'sa_token': input_list[0]['value'],
            'uuid': input_list[1]['value'],
            '_t': input_list[4]['value'],
            'loginType': input_list[5]['value'],
            'pubKey': input_list[7]['value'],
            'eid': self.eid,
            'fp': self.fp,
        }

    def login_by_username(self):
        if self.is_login:
            logger.info('登录成功')
            return True

        username = input('账号:')
        password = input('密码:')
        if (not username) or (not password):
            logger.error('用户名或密码不能为空')
            return False
        self.username = username

        data = self._get_login_data()
        uuid = data['uuid']

        auth_code = ''
        if self._need_auth_code(username):
            logger.info('本次登录需要验证码')
            auth_code = self._get_auth_code(uuid)
        else:
            logger.info('本次登录不需要验证码')
        login_url = "https://passport.jd.com/uc/loginService"
        payload = {
            'uuid': uuid,
            'version': 2015,
            'r': random.random(),
        }
        data['authcode'] = auth_code
        data['loginname'] = username
        data['nloginpwd'] = Util.encrypt_pwd(password)
        headers = {
            'User-Agent': self.default_user_agent,
            'Origin': 'https://passport.jd.com',
        }
        resp = self.session.post(url=login_url, data=data, headers=headers, params=payload)

        if not Util.response_status(resp):
            logger.error('登录失败')
            return False

        if not self._get_login_result(resp):
            return False

    def _need_auth_code(self, username):
        url = 'https://passport.jd.com/uc/showAuthCode'
        data = {
            'loginName': username,
        }
        payload = {
            'version': 2015,
            'r': random.random(),
        }
        resp = self.session.post(url, params=payload, data=data, headers=self.headers)
        if not Util.response_status(resp):
            logger.error('获取是否需要验证码失败')
            return False

        resp_json = json.loads(resp.text[1:-1])  # ({"verifycode":true})
        return resp_json['verifycode']

    def _get_login_result(self, resp):
        resp_json = Util.parse_json(resp.text)
        error_msg = ''
        if 'success' in resp_json:
            # {"success":"http://www.jd.com"}
            return True
        elif 'emptyAuthcode' in resp_json:
            # {'_t': '_t', 'emptyAuthcode': '请输入验证码'}
            # {'_t': '_t', 'emptyAuthcode': '验证码不正确或验证码已过期'}
            error_msg = resp_json['emptyAuthcode']
        elif 'username' in resp_json:
            # {'_t': '_t', 'username': '账户名不存在，请重新输入'}
            # {'username': '服务器繁忙，请稍后再试', 'venture': 'xxxx', 'p': 'xxxx', 'ventureRet': 'http://www.jd.com/', '_t': '_t'}
            if resp_json['username'] == '服务器繁忙，请稍后再试':
                error_msg = resp_json['username'] + '(预计账户存在风险，需短信激活)'
            else:
                error_msg = resp_json['username']
        elif 'pwd' in resp_json:
            # {'pwd': '账户名与密码不匹配，请重新输入', '_t': '_t'}
            error_msg = resp_json['pwd']
        else:
            error_msg = resp_json
        logger.error(error_msg)
        return False

    def _get_QRcode(self) -> bool:
        """
        获取二维码
        """
        url = 'https://qr.m.jd.com/show'
        payload = {
            'appid': 133,
            'size': 147,
            't': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://passport.jd.com/new/login.aspx',
        }
        resp = self.session.get(url=url, headers=headers, params=payload)
        if not Util.response_status(resp):
            logger.info('获取二维码失败')
            return False
        QRCode_file = 'happyCatQRCode.png'
        Util.save_image(resp, QRCode_file)
        logger.info('二维码获取成功，请打开京东APP扫描')
        # Util.open_image(QRCode_file)
        Util.open_image("ui/happt_cat_QRcode.html")
        return True

    def _get_QRcode_ticket(self):
        """
        获取二维码认证
        """
        url = 'https://qr.m.jd.com/check'
        payload = {
            'appid': '133',
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'token': self.session.cookies.get('wlfstk_smdl'),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://passport.jd.com/new/login.aspx',
        }
        resp = self.session.get(url=url, headers=headers, params=payload)

        if not Util.response_status(resp):
            logger.error('快乐喵警告:获取二维码扫描结果异常')
            return False
        logger.info(resp.text)
        resp_json = Util.parse_json(resp.text)
        if resp_json['code'] != 200:
            logger.info(f'快乐喵提示:二维码扫描结果状态码: {resp_json["code"]}, 扫描结果信息: {resp_json["msg"]}' )
            return None
        else:
            logger.info('快乐喵提示: 恭喜完成手机客户端确认！！！')
            return resp_json['ticket']

    def _validate_QRcode_ticket(self, ticket):
        """
        校验二维码
        """
        url = 'https://passport.jd.com/uc/qrCodeTicketValidation'
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://passport.jd.com/uc/login?ltype=logout',
        }
        resp = self.session.get(url=url, headers=headers, params={'t': ticket})

        if not Util.response_status(resp):
            return False

        resp_json = json.loads(resp.text)
        if resp_json['returnCode'] == 0:
            return True
        else:
            logger.info(resp_json)
            return False

    def login_by_QRcode(self):
        """二维码登陆
        :return:
        """
        if self.is_login:
            logger.info('登录成功')
            return

        self._get_login_page()

        # download QR code
        if not self._get_QRcode():
            raise HappyCatException('二维码下载失败')

        # get QR code ticket
        ticket = None
        retry_times = 85
        for _ in range(retry_times):
            ticket = self._get_QRcode_ticket()
            if ticket:
                break
            time.sleep(2)
        else:
            raise HappyCatException('二维码过期，请重新获取扫描')

        # validate QR code ticket
        if not self._validate_QRcode_ticket(ticket):
            raise HappyCatException('二维码信息校验失败')

        logger.info('二维码登录成功')
        self.is_login = True
        self.nick_name = self.get_username()
        self._save_cookies()