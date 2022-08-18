from config import config
from ecloud import Cloud
from push import push


def main(*arg):
    pushType = config.get("push")
    key = config.get("key")

    msg = []
    for u in config.get("multi"):
        e = Cloud(u["account"], u["password"])
        res = e.start()
        msg.extend(res)

    if pushType:
        push(pushType, key, "天翼云网盘签到", msg)


if __name__ == "__main__":
    main()
