import base64
import time
import requests as req
from tools import b64ToHex
from re import compile
import rsa


def handler(fn):
    def inner(*args, **kwargs):
        res = fn(*args, **kwargs)

        return [
            {
                "h4": {
                    "content": res["account"],
                },
                "table": {
                    "content": [
                        ("描述", "内容"),
                        ("签到奖励", f"{res['reward']}M"),
                        ("第一次抽奖", res["prize1"]),
                        ("第二次抽奖", res["prize2"]),
                    ]
                },
            },
        ]

    return inner


class Cloud:
    LOGIN = "https://cloud.189.cn/api/portal/loginUrl.action"
    SUBMIT = "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do"
    SIGN = "https://api.cloud.189.cn/mkt/userSign.action"

    def __init__(self, account, password):
        self.account = account
        self.password = password
        self.client = req.Session()

    @handler
    def start(self):
        res = self.checkIn()
        res.update({"account": self.account})
        return res

    def checkIn(self):
        self.login()

        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)",  # noqa: E501
            "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",  # noqa: E501
            "Host": "m.cloud.189.cn",
            "Accept-Encoding": "gzip, deflate",
        }

        resp = self.client.get(
            Cloud.SIGN,
            params={
                "rand": str(round(time.time() * 1000)),
                "clientType": "TELEANDROID",
                "version": "8.6.3",
            },
            headers=headers,
        ).json()

        reward = resp["netdiskBonus"]

        if resp["isSign"] == "false":
            print(f"签到获得 {reward}M 空间")
        else:
            print(f"已经签到过了, 签到获得 {reward}M 空间")

        url1 = "https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN&activityId=ACT_SIGNIN"  # noqa: E501
        url2 = "https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN_PHOTOS&activityId=ACT_SIGNIN"  # noqa: E501

        # 两次抽奖
        prizes = []
        for u in [url1, url2]:
            resp = self.client.get(u, headers=headers).json()

            if "errorCode" in resp:
                msg = resp["errorCode"]
                print(msg)
                prizes.append(msg)
            else:
                prize = resp.get("prizeName")
                print(f"抽奖获得 {prize}")

                prizes.append(prize)

        return {
            "reward": reward,
            "prize1": prizes[0],
            "prize2": prizes[1],
        }

    @staticmethod
    def rsa_encode(rsaKey, string):
        rsaKey = f"-----BEGIN PUBLIC KEY-----\n{rsaKey}\n-----END PUBLIC KEY-----"  # noqa: E501
        pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(rsaKey.encode())
        result = b64ToHex(
            base64.b64encode(rsa.encrypt(string.encode(), pubkey)).decode()
        )

        return result

    # 抽取关键字
    @staticmethod
    def extract(raw: str, regEx: str) -> str | None:
        res = compile(regEx).findall(raw)

        if len(res) != 0:
            return res[0]

    # 登录
    def login(self):
        resp = self.client.get(
            Cloud.LOGIN,
            params={
                "redirectURL": "https://cloud.189.cn/web/redirect.html?returnURL=/main.action",  # noqa: E501
            },
        )

        captchaToken = self.extract(resp.text, "'captchaToken' value='(.+?)'")
        lt = self.extract(resp.text, 'lt = "(.+?)"')
        returnUrl = self.extract(resp.text, "returnUrl = '(.+?)'")
        paramId = self.extract(resp.text, 'paramId = "(.+?)"')
        j_rsakey = self.extract(resp.text, '"j_rsaKey" value="(.+?)"')

        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)",  # noqa: E501
            "Referer": "https://open.e.189.cn/",
            "lt": lt,
        }

        data = {
            "appKey": "cloud",
            "accountType": "01",
            "userName": f"{{RSA}}{self.rsa_encode(j_rsakey, self.account)}",
            "password": f"{{RSA}}{self.rsa_encode(j_rsakey, self.password)}",
            "validateCode": "",
            "captchaToken": captchaToken,
            "returnUrl": returnUrl,
            "mailSuffix": "@189.cn",
            "paramId": paramId,
        }

        resp = self.client.post(
            Cloud.SUBMIT,
            data=data,
            headers=headers,
            timeout=5,
        ).json()

        print(resp.get("msg"))

        self.client.get(resp["toUrl"])
