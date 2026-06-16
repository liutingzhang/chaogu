"""
限价委托独立脚本 — 与市价委托完全解耦
科创板、北交所等只支持限价委托的板块使用此脚本

与 agent_trader.py 的区别：
1. 直接走【买入[F1]】/【卖出[F2]】限价委托菜单
2. 不点重填按钮（限价界面没有）
3. 先清空股票代码框再输入
4. 先清空价格框（系统会自动填当前市价）再输入委托价
5. 直接点【买入】/【卖出】按钮，不操作市价申报方式ComboBox

前置条件：
    1. 同花顺 xiadan.exe 已打开并登录（选"模拟炒股"账户即模拟盘）
    2. 交易服务已启动
    3. 同花顺窗口不要最小化
"""

import json
import re
from typing import Any, Dict

import requests

BASE_URL = "http://127.0.0.1:6003"
DEFAULT_STRATEGY_NO = "agent_limit"
ALLOWED_OPERATES = {"buy", "sell"}


def limit_buy(code: str, name: str, amount: int, price: float, strategy_no: str = DEFAULT_STRATEGY_NO):
    """ 限价委托买入（科创板/北交所专用）"""
    return place_order("buy", code, name, amount, strategy_no, price=price)


def limit_sell(code: str, name: str, amount: int, price: float, strategy_no: str = DEFAULT_STRATEGY_NO):
    """ 限价委托卖出"""
    return place_order("sell", code, name, amount, strategy_no, price=price)


def place_order(operate: str, code: str, name: str, amount: int, strategy_no: str = DEFAULT_STRATEGY_NO, price: float = None):
    order = validate_order({
        "operate": operate,
        "code": code,
        "name": name,
        "amount": amount,
        "strategy_no": strategy_no,
        "price": price,
    })
    # 强制走限价委托标识
    payload = {
        "strategy_no": order["strategy_no"],
        "code": order["code"],
        "name": order["name"],
        "ct_amount": order["amount"],
        "operate": order["operate"],
        "order_type": "limit",
        "price": str(order["price"]),
    }
    return _post("/api/queue", [payload])


def validate_order(order: Dict[str, Any]):
    """ 校验参数 """
    operate = str(order.get("operate", "")).strip().lower()
    if operate not in ALLOWED_OPERATES:
        raise ValueError(f"operate 只能是 {sorted(ALLOWED_OPERATES)}")

    code = str(order.get("code", "")).strip()
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("股票代码必须是6位数字")

    name = str(order.get("name", "")).strip()
    if not name:
        raise ValueError("股票名称不能为空")

    amount = int(order.get("amount", 0))
    board = get_board_info(code)
    if amount < board["min_amount"]:
        raise ValueError(f"{board['name']}股票最小申报数量为{board['min_amount']}股，当前{amount}股不足")

    price = order.get("price")
    if price is None or price <= 0:
        raise ValueError("限价委托必须提供价格，且价格>0")

    return {
        "operate": operate,
        "code": code,
        "name": name,
        "amount": amount,
        "price": float(price),
        "strategy_no": str(order.get("strategy_no", DEFAULT_STRATEGY_NO)).strip() or DEFAULT_STRATEGY_NO,
    }


# 限价委托支持的板块（科创板、北交所必须用此脚本）
BOARDS_LIMIT_ONLY = {
    "star": {"name": "科创板", "min_amount": 200},
    "bse": {"name": "北交所", "min_amount": 100},
}

# 也支持主板、创业板（用户主动要求限价时）
BOARDS_LIMIT_OPTIONAL = {
    "sh_main": {"name": "沪主板", "min_amount": 100},
    "sz_main": {"name": "深主板", "min_amount": 100},
    "chinext": {"name": "创业板", "min_amount": 100},
}


def get_board_type(code: str) -> str:
    c = str(code).strip()
    if c.startswith("688"):
        return "star"
    elif c.startswith("60"):
        return "sh_main"
    elif c.startswith("00"):
        return "sz_main"
    elif c.startswith("300"):
        return "chinext"
    elif c.startswith("8") or c.startswith("4"):
        return "bse"
    return "unknown"


def get_board_info(code: str) -> dict:
    t = get_board_type(code)
    if t in BOARDS_LIMIT_ONLY:
        return BOARDS_LIMIT_ONLY[t]
    if t in BOARDS_LIMIT_OPTIONAL:
        return BOARDS_LIMIT_OPTIONAL[t]
    return {"name": "未知板块", "min_amount": 100}


def _post(path, data):
    try:
        r = requests.post(f"{BASE_URL}{path}", json=data, timeout=30)
        try:
            return r.json()
        except Exception:
            return {"code": -1, "msg": f"HTTP {r.status_code} 非JSON响应: {r.text[:300]}", "data": None}
    except Exception as e:
        return {"code": -1, "msg": str(e), "data": None}


if __name__ == "__main__":
    import sys

    usage = """用法:
  python limit_trader.py buy  代码 名称 数量 价格 [策略编号]
  python limit_trader.py sell 代码 名称 数量 价格 [策略编号]

示例:
  python limit_trader.py buy  688262 国芯科技 200 35.78   # 科创板限价买入
  python limit_trader.py buy  830001 北交所股 100 10.00   # 北交所限价买入
  python limit_trader.py sell 300666 江丰电子 100 26.00   # 限价卖出
"""

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in ("buy", "sell"):
        print(f"未知命令: {cmd}\n{usage}")
        sys.exit(1)

    code, name, amount, price = sys.argv[2], sys.argv[3], int(sys.argv[4]), float(sys.argv[5])
    sn = sys.argv[6] if len(sys.argv) > 6 else DEFAULT_STRATEGY_NO

    if cmd == "buy":
        result = limit_buy(code, name, amount, price, sn)
    else:
        result = limit_sell(code, name, amount, price, sn)

    print(json.dumps(result, ensure_ascii=False, indent=2))
