---
name: "ths-trade-agent"
description: "使用 ths_trade 操作同花顺进行股票买卖、查询。当用户要求操作同花顺交易、模拟炒股、自动化下单时调用。"
---

# ths_trade Agent 操作指南

## 概述

`D:\ths_trade\agent_trader.py` 是对 ths_trade 项目的极简封装，4 个函数覆盖全部交易操作。

**架构**：`Agent 调用函数 → HTTP POST → app.py(6003端口) → pywinauto → 同花顺 xiadan.exe`

## 前置条件（先提醒用户完成）

1. 同花顺 `xiadan.exe` 已打开并登录（选"模拟炒股"即模拟盘）
2. `app.py` 交易服务已启动：双击 `D:\ths_trade\start.bat`

## Agent 调用方式（一条 import + 函数调用）

```python
import sys; sys.path.insert(0, r"D:\ths_trade")
from agent_trader import buy, sell, batch, query
```

## 4 个函数

### 1. `buy(code, name, amount)` — 市价买入

```python
buy("600000", "浦发银行", 100)
# amount 必须是 100 的整数倍
```

### 2. `sell(code, name, amount)` — 市价卖出

```python
sell("162411", "华宝油气", 200)
# amount 必须是 100 的整数倍
```

### 3. `batch(orders)` — 批量下单

```python
batch([
    {"code": "600000", "name": "浦发银行", "amount": 100, "operate": "buy"},
    {"code": "162411", "name": "华宝油气", "amount": 200, "operate": "sell"},
])
```

### 4. `query()` — 查询成交记录

```python
query()           # 查 agent 策略的全部成交
query("strategy1")  # 按策略编号查
```

## 返回格式

**buy/sell/batch 返回**：
```json
{"code": 200, "msg": "success", "data": "agent"}
```
返回 `code=200` 表示下单指令已进入队列，交易异步执行（约 3 秒/单）。

**query 返回**：
```json
{"code": 200, "msg": "success", "data": [
    {"证券代码":"600000","证券名称":"浦发银行","操作":"买入","委托数量":"100","成交数量":"0","合同编号":"...","策略编号":"agent","备注":"..."},
    ...
]}
```
返回 `code=200` 但 `data=[]` 表示尚无成交记录。

**错误返回**：
```json
{"code": -1, "msg": "ConnectionError ...", "data": null}
```
表示交易服务未启动。

## 命令行调用（测试用）

```powershell
cd D:\ths_trade
python agent_trader.py buy  600000 浦发银行 100
python agent_trader.py sell 162411 华宝油气 200
python agent_trader.py query
```

## 注意事项

- **amount 必须是 100 的整数倍**（A 股 1 手 = 100 股）
- 单笔交易约 3 秒，多单自动排队依次执行
- 同花顺窗口不可最小化
- 模拟炒股：同花顺登录时选择"模拟炒股"账户
- 返回 `code=-1` 表示服务未启动或网络不通，先检查 `start.bat` 是否运行
- 交易是**异步**的：buy/sell 返回只表示入队成功，实际成交结果用 query() 查询