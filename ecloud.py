import random
import requests as req
import rsa
from tools import failed, success, b64ToHex
from base64 import b64encode
from urllib.parse import urlparse, parse_qs
from time import time, sleep

KEY = "-----BEGIN PUBLIC KEY-----\n<% pubkey %>\n-----END PUBLIC KEY-----"

BASE_URL = "https://open.e.189.cn"


class ecloud:
    def __init__(self, **config):
        self.account = config.get("account")
        self.password = config.get("password")
        self.client = req.Session()
        self.init()

    def init(self):
        resp = req.post(
            f"{BASE_URL}/api/logbox/config/encryptConf.do",
            data={"appId": "cloud"},
        ).json()

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
        resp = req.post(
            f"{BASE_URL}/api/logbox/oauth2/appConf.do",
            data={"version": 2.0, "appKey": "cloud"},
            headers={"lt": lt, "reqId": reqId},
        ).json()

        if resp.get("result") == "0":
            success("get app config.")
        else:
            failed("get app config.")

        return resp.get("data")

    @staticmethod
    def lt_reqid_url():
        resp = req.get(
            "https://cloud.189.cn/api/portal/loginUrl.action",
            params={"redirectURL": "https://cloud.189.cn/web/redirect.html"},
            allow_redirects=True,
        )

        url = urlparse(resp.url)
        query = parse_qs(url.query)
        lt = query.get("lt")[0]
        reqId = query.get("reqId")[0]

        return lt, reqId, resp.url

    def encrypt(self, s: str):
        b = rsa.encrypt(s.encode(), self.pubkey)
        return f"{self.pre}{b64ToHex(b64encode(b).decode())}"

    def login(self):
        self.lt, self.reqId, url = ecloud.lt_reqid_url()

        resp = ecloud.app_config(self.lt, self.reqId)

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
            f"{BASE_URL}/api/logbox/oauth2/loginSubmit.do",
            data=data,
            headers=self.headers,
            timeout=5,
        ).json()

        if resp.get("result") == 0:
            success(resp.get("msg"))
        else:
            failed("Login failed.")

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
            "https://api.cloud.189.cn/mkt/userSign.action",
            params={
                "rand": str(round(time() * 1000)),
                "clientType": "TELEANDROID",
                "version": "8.6.3",
            },
            headers=headers,
        ).json()

        if "errorCode" in resp:
            reward = f"【签到】{resp.get('errorCode')}, {resp.get('errorMsg')}"
            failed(reward)
        else:
            r = resp.get("netdiskBonus")

            if resp.get("isSign"):
                reward = f"【已签】获得{r}M空间"
            else:
                reward = f"【签到】获得{r}M空间"

            success(reward)

        prizes = []

        urls = [
            "https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN&activityId=ACT_SIGNIN",
            "https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN_PHOTOS&activityId=ACT_SIGNIN",
            "https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_2022_FLDFS_KJ&activityId=ACT_SIGNIN",
        ]

        for idx, u in enumerate(urls):
            resp = self.client.get(u, headers=headers).json()
            # print(resp)

            if "prizeName" in resp:
                p = resp.get("prizeName")
                prize = f"【抽奖{idx+1}】{p}"
                success(prize)
                prizes.append(prize)
            else:
                if "errorCode" in resp:
                    p = f"【抽奖{idx+1}】{resp.get('errorCode')}"
                    errorMsg = resp.get("errorMsg")
                    failed(p, errorMsg)
                    prizes.append(p)
                elif "error" in resp:
                    p = f"【抽奖{idx+1}】{resp.get('error')}"
                    failed(p)
                    prizes.append(p)

                sleep(random.randint(5, 10))

        return {
            "reward": reward,
            "prizes": prizes,
        }

    def start(self):
        res = self.checkIn()

        msg = [
            {
                "h4": {
                    "content": "天翼云盘签到小助手",
                },
                "txt": {
                    "content": f"【账号】{self.account}",
                },
            },
            {
                "txt": {
                    "content": res.get("reward"),
                },
            },
        ]

        for p in res["prizes"]:
            msg.append(
                {
                    "txt": {
                        "content": p,
                    }
                }
            )

        return {"title": "天翼云盘签到小助手", "message": msg}
