## 天翼云签到(云函数版)

注意把子模块也一起下载

```bash
git clone --recursive https://github.com/arcturus-script/ecloud.git
```

### 步骤

1. 选择 `python3.7`, 改执行方法为 `index.main`

2. ctrl + ` 进入终端

3. 输入 `pip3 install -r ./src/requirements.txt -t ./src` 安装依赖( 这个路径每个云函数可能不一样, 总之就是把依赖下到 index.py 的目录 )
