# Global Futures Trend Lab V1.0

面向历史期货行情研究的 Streamlit 网页应用。它不连接交易账户、不下单、不承诺收益；技术评分只是可解释的历史规则。

## 本地运行

安装 Python 3.11，打开命令行并进入项目目录：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

浏览器打开命令行显示的本机地址。首次行情请求需要网络；请求失败时仍可通过“数据管理”上传 CSV。

## 给零基础用户的云端部署步骤（Streamlit Community Cloud）

### 1. 创建 GitHub 账户

浏览器打开 [github.com](https://github.com)，选择 **Sign up**，按页面提示填写邮箱、密码并完成验证。

### 2. 创建仓库

登录 GitHub 后点击右上角 **+** → **New repository**。仓库名称可填 `global-futures-trend-lab`，选择 **Public**（Streamlit 免费部署通常要求公开仓库），不要勾选自动添加 README（项目已有 README），然后点击 **Create repository**。

### 3. 上传项目文件

进入本项目文件夹 `global-futures-trend-lab`，在 GitHub 新仓库页面选择 **Add file** → **Upload files**，把文件夹中的全部文件和子文件夹拖入上传区域。确认能看到 `app.py`、`requirements.txt`、`README.md`、`src/`、`config/` 和 `tests/`，在页面下方点 **Commit changes**。

也可以在电脑安装 GitHub Desktop，登录后选择 **Add an Existing Repository**，选中项目目录；如果显示不是仓库，选择创建仓库，再按提示 **Publish repository**。发布前确认 `.gitignore` 生效，不要上传密码或秘密文件。

### 4. 打开 Streamlit Community Cloud

访问 [share.streamlit.io](https://share.streamlit.io)，点击 **Sign up** 或 **Sign in**。建议选 **Continue with GitHub**。

### 5. 连接 GitHub

按页面授权 Streamlit 访问 GitHub。若仓库列表没有显示，回 GitHub 的 **Settings → Applications** 检查 Streamlit 权限，或者在 Streamlit 页面重新连接账户。

### 6. 选择应用入口

在 Streamlit 页面点击 **Create app**，选择 **Yup, I have an app**。填写刚上传的仓库、分支（通常是 `main`）和主文件路径 `app.py`。部署前打开 **Advanced settings**，将 Python 版本设为 3.11；Python 版本在应用创建后不能直接更换，需删除并重新部署。可选填一个容易记的公网子域名。

### 7. 部署

点击 **Deploy!**。首次安装依赖需要数分钟。部署成功后页面会显示应用公网地址。

### 8. 打开网页

点击生成的 URL，等待应用启动。进入“全球市场总览”点击加载按钮逐个请求候选代码；数据源可能拒绝或限制请求。发生失败时，可从“数据管理”导入 CSV。

### 9. 查看日志与重新部署

在应用页面右下角菜单中选择 **Manage app**，查看 **Logs**。日志中的 `ModuleNotFoundError` 通常表示依赖安装失败；确认仓库根目录有 `requirements.txt` 后点击 **Reboot app**。改代码后将新文件提交（commit）到所选分支，Streamlit 通常会自动重新部署；也可在 **Manage app** 选择重启。

## 数据和指标说明

`config/markets.json` 初始列出 30 个 Yahoo Finance 候选代码。代码是否有效不可预先保证，网页会逐个尝试并分别显示失败原因；失败不会以其他代码或随机数补值。Yahoo 免费历史数据可能延迟、缺行、限频；期货连续合约的拼接与调整方法也可能影响历史比较。不能用于结算或执行交易。

CSV 必须有 `Date, Open, High, Low, Close, Volume` 六列；日期可用 `YYYY-MM-DD`。程序检查日期、数值、负成交量和 OHLC 关系，重复日期保留最后记录。日线可聚合为周线，当前所在周会标记为未完成。上传数据仅保存在当前应用会话内存，云端重启可能清空；应用不把数据写入持久磁盘。

均线要求完整窗口，MACD、RSI、ATR 在预热期保留缺失值。评分 5 项分别是收盘价/MA20、MA20/MA50、MA50/MA100、当前/五期前 MA20、MACD 柱体方向，各项多头 +1、空头 -1；缺少任一项时总体显示“数据不足”。评分不是盈利概率或买卖指令。

## 测试

在项目目录执行 `python -m pytest -q`。测试只使用明确的合成 OHLCV 数据，不会显示为市场行情。

## 文件结构

```text
app.py                 Streamlit 页面
src/data_provider.py   Yahoo Finance 下载与失败隔离
src/indicators.py      OHLCV 校验、指标和周线聚合
src/trend_engine.py    可解释的趋势评分
config/markets.json    候选品种清单
tests/                 指标和评分单元测试
```
