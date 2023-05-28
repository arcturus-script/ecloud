import string


def handler(fn):
    def inner(*args, **kwargs):
        res = fn(*args, **kwargs)

        return [
            {
                "h4": {
                    "content": res["account"],
                },
                "table": {
                    "contents": [
                        ("描述", "内容"),
                        ("签到奖励", f"{res['reward']}M"),
                        ("第一次抽奖", res["prize1"]),
                        ("第二次抽奖", res["prize2"]),
                    ]
                },
            },
        ]

    return inner


def _chr(a):
    return f"{string.digits}{string.ascii_lowercase}"[a]


b64map = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def b64ToHex(a):
    d = ""
    e = 0
    c = 0
    for i in range(len(a)):
        if list(a)[i] != "=":
            v = b64map.index(list(a)[i])
            if 0 == e:
                e = 1
                d += _chr(v >> 2)
                c = 3 & v
            elif 1 == e:
                e = 2
                d += _chr(c << 2 | v >> 4)
                c = 15 & v
            elif 2 == e:
                e = 3
                d += _chr(c)
                d += _chr(v >> 2)
                c = 3 & v
            else:
                e = 0
                d += _chr(c << 2 | v >> 4)
                d += _chr(15 & v)
    if e == 1:
        d += _chr(c << 2)
    return d


def failed(*args, **kwargs):
    print("[\033[31mfailed\033[0m]  ", end="")
    print(*args, **kwargs)


def success(*args, **kwargs):
    print("[\033[32msuccess\033[0m] ", end="")
    print(*args, **kwargs)


def info(*args, **kwargs):
    print("[\033[34minfo\033[0m]    ", end="")
    print(*args, **kwargs)
