import requests as req
import rsa
from tools import failed, handler, success, b64ToHex
from base64 import b64encode
from urllib.parse import urlparse, parse_qs
from time import time

KEY = "-----BEGIN PUBLIC KEY-----\n<% pubkey %>\n-----END PUBLIC KEY-----"

BASE_URL = "https://open.e.189.cn"

APP_CONFIG = f"{BASE_URL}/api/logbox/oauth2/appConf.do"

NEED_CAPTCHA = f"{BASE_URL}/api/logbox/oauth2/needcaptcha.do"

ENCRYPT = f"{BASE_URL}/api/logbox/config/encryptConf.do"

LOGIN_SUBMIT = f"{BASE_URL}/api/logbox/oauth2/loginSubmit.do"

USER_SIGN = "https://api.cloud.189.cn/mkt/userSign.action"

LOGIN_URL = "https://cloud.189.cn/api/portal/loginUrl.action?redirectURL=https://cloud.189.cn/web/redirect.html"

U1 = "https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN&activityId=ACT_SIGNIN"

U2 = "https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN_PHOTOS&activityId=ACT_SIGNIN"

class Cloud:
    def __init__(self, **config):
        self.account = config.get("account")
        self.password = config.get("password")
        self.client = req.Session()
        self.init()

    def init(self):
        resp = req.post(ENCRYPT, data={"appId": "cloud"}).json()

        if resp.get("result") == 0:
            success("get encrypt config.")
            
            pubkey_str = resp.get("data").get("pubKey")
            self.pre = resp.get("data").get("pre")

            pubkey = KEY.replace("<% pubkey %>", pubkey_str).encode()
            self.pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(pubkey)

        else:
            failed("can not get encrypt config.")

    @staticmethod
    def app_config(lt: str, reqId: str):
        data = {"version": 2.0, "appKey": "cloud"}
        headers = {"lt": lt, "reqId": reqId}
        resp = req.post(APP_CONFIG, data=data, headers=headers).json()

        if resp.get("result") == "0":
            success("get app config.")
        else:
            failed("get app config.")

        return resp.get("data")

    @staticmethod
    def lt_reqid_url():
        resp = req.get(LOGIN_URL, allow_redirects=True)

        url = urlparse(resp.url)
        query = parse_qs(url.query)
        lt = query.get("lt")[0]
        reqId = query.get("reqId")[0]

        return lt, reqId, resp.url

    def encrypt(self, s: str):
        b = rsa.encrypt(s.encode(), self.pubkey)
        return f"{self.pre}{b64ToHex(b64encode(b).decode())}"

    def login(self):
        self.lt, self.reqId, url = Cloud.lt_reqid_url()

        resp = Cloud.app_config(self.lt, self.reqId)

        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.57",
            "origin": "https://open.e.189.cn",
            "referer": url,
            "lt": self.lt,
            "reqid": self.reqId,
        }

        data = {
            "version": "v2.0",
            "apToken": "",
            "appKey": "cloud",
            "accountType": "01",
            "userName": self.encrypt(self.account),
            "password": self.encrypt(self.password),
            "validateCode": "",
            "captchaToken": "",
            "returnUrl": resp.get("returnUrl"),
            "mailSuffix": "@189.cn",
            "dynamicCheck": "FALSE",
            "clientType": "1",
            "cb_SaveName": "0",
            "isOauth2": "false",
            "state": "",
            "paramId": resp.get("paramId"),
        }

        resp = self.client.post(
            LOGIN_SUBMIT,
            data=data,
            headers=self.headers,
            timeout=5,
        ).json()

        if resp.get("result") == 0:
            success(resp.get("msg"))
        else:
            failed("登录失败")

        self.client.get(resp.get("toUrl"))

    def checkIn(self):
        self.login()

        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)",
            "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
            "Host": "m.cloud.189.cn",
            "Accept-Encoding": "gzip, deflate",
        }

        resp = self.client.get(
            USER_SIGN,
            params={
                "rand": str(round(time() * 1000)),
                "clientType": "TELEANDROID",
                "version": "8.6.3",
            },
            headers=headers,
        ).json()

        reward = resp.get("netdiskBonus")

        if not resp.get("isSign"):
            success(f"签到获得 {reward}M 空间")
        else:
            success(f"已经签到过了, 签到获得 {reward}M 空间")

        prizes = []

        for u in [U1, U2]:
            resp = self.client.get(u, headers=headers).json()

            if "errorCode" in resp:
                msg = resp.get("errorCode")

                failed(msg)

                prizes.append(msg)
            else:
                prize = resp.get("prizeName")

                success(f"抽奖获得{prize}")

                prizes.append(prize)

        return {
            "reward": reward,
            "prize1": prizes[0],
            "prize2": prizes[1],
        }

    @handler
    def start(self):
        res = self.checkIn()
        res.update({"account": self.account})

        return res
