"""
ths_trade Agent 操作脚本 — 极简解耦版
每个操作都是独立函数，Agent 只需 import 调用。

前置条件：
    1. 同花顺 xiadan.exe 已打开并登录（选"模拟炒股"账户即模拟盘）
    2. app.py 交易服务已启动（双击 D:\ths_trade\start.bat）

设计目标：
    - 不写死股票、数量、策略编号
    - 支持结构化下单，也支持自然语言解析成下单指令
    - 默认极简模式：只负责把买/卖指令送入同花顺并自动确认到 Y
"""

import json
import re
from typing import Any, Dict, List

import requests

BASE_URL = "http://127.0.0.1:6003"
LOT_SIZE = 100
STAR_MARKET_LOT_SIZE = 200  # 科创板最小申报数量
DEFAULT_STRATEGY_NO = "agent"
ALLOWED_OPERATES = {"buy", "sell"}

# A股板块交易规则
BOARD_RULES = {
    "sh_main": {  # 沪主板 (60xxxx)
        "name": "沪主板",
        "min_amount": 100,
        "amount_step": 100,       # 必须100股整数倍
        "market_order": True,     # 支持市价委托
        "price_limit_pct": 10,    # 涨跌幅10%
    },
    "star": {  # 科创板 (688xxx)
        "name": "科创板",
        "min_amount": 200,
        "amount_step": 1,         # 超200股可按1股递增
        "market_order": False,    # 科创板市价委托需保护限价，默认走限价委托
        "market_order_note": "科创板默认走限价委托，需要提供委托价格",
        "price_limit_pct": 20,    # 涨跌幅20%
    },
    "sz_main": {  # 深主板 (00xxxx)
        "name": "深主板",
        "min_amount": 100,
        "amount_step": 100,
        "market_order": True,
        "price_limit_pct": 10,
    },
    "chinext": {  # 创业板 (300xxx)
        "name": "创业板",
        "min_amount": 100,
        "amount_step": 100,
        "market_order": True,
        "price_limit_pct": 20,    # 涨跌幅20%
    },
    "bse": {  # 北交所 (8xxxxx / 4xxxxx)
        "name": "北交所",
        "min_amount": 100,
        "amount_step": 100,
        "market_order": False,    # 北交所不支持市价委托
        "market_order_note": "北交所仅支持限价委托，不支持市价委托",
        "price_limit_pct": 30,    # 涨跌幅30%
    },
    "unknown": {  # 未知板块
        "name": "未知板块",
        "min_amount": 100,
        "amount_step": 100,
        "market_order": True,
        "price_limit_pct": 10,
    },
}


def get_board_type(code: str) -> str:
    """根据股票代码判断所属板块"""
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
    else:
        return "unknown"


def get_board_info(code: str) -> dict:
    """获取股票所属板块的交易规则"""
    return BOARD_RULES.get(get_board_type(code), BOARD_RULES["unknown"])


def buy(code: str, name: str, amount: int, price: float = None, strategy_no: str = DEFAULT_STRATEGY_NO):
    return place_order("buy", code, name, amount, strategy_no, price=price)


def sell(code: str, name: str, amount: int, price: float = None, strategy_no: str = DEFAULT_STRATEGY_NO):
    return place_order("sell", code, name, amount, strategy_no, price=price)


def place_order(operate: str, code: str, name: str, amount: int, strategy_no: str = DEFAULT_STRATEGY_NO, price: float = None):
    order = normalize_order({
        "operate": operate,
        "code": code,
        "name": name,
        "amount": amount,
        "strategy_no": strategy_no,
        "price": price,
    })
    return _post_queue([
        _make_order(
            order["operate"],
            order["code"],
            order["name"],
            order["amount"],
            order["strategy_no"],
            order_type=order["order_type"],
            price=order.get("price"),
        )
    ])


def batch(orders: List[Dict[str, Any]], strategy_no: str = DEFAULT_STRATEGY_NO):
    normalized_orders = [
        normalize_order({**o, "strategy_no": o.get("strategy_no", strategy_no)})
        for o in orders
    ]
    data = [
        _make_order(o["operate"], o["code"], o["name"], o["amount"], o["strategy_no"])
        for o in normalized_orders
    ]
    return _post_queue(data)


def cancel(entrust_no: str, strategy_no: str = DEFAULT_STRATEGY_NO):
    """
    entrust_no: 合同编号/委托编号
    """
    order = {
        "strategy_no": strategy_no,
        "code": str(entrust_no).strip(),
        "name": "撤单",
        "ct_amount": 0,
        "operate": "cancel",
    }
    return _post_queue([order])


def query(strategy_no: str = DEFAULT_STRATEGY_NO):
    body = {"strategy_no": strategy_no, "operate": "get_today_entrusts"}
    return _post("/api/search", body)


def preview_order(operate: str, code: str, name: str, amount: int, price: float = None, strategy_no: str = DEFAULT_STRATEGY_NO):
    return normalize_order({
        "operate": operate,
        "code": code,
        "name": name,
        "amount": amount,
        "strategy_no": strategy_no,
        "price": price,
    })


def parse_trade_text(text: str, strategy_no: str = DEFAULT_STRATEGY_NO):
    """
    解析简单自然语言。
    示例：
        买江丰电子100股 300666
        卖出 中国平安 200股 601318
        买入 江丰电子 一手 300666
    """
    raw = str(text).strip()
    compact = re.sub(r"\s+", "", raw)

    if compact.startswith(("买", "买入")):
        operate = "buy"
    elif compact.startswith(("卖", "卖出")):
        operate = "sell"
    else:
        raise ValueError("无法识别买卖方向，请使用‘买/买入/卖/卖出’开头")

    code_match = re.search(r"(\d{6})", compact)
    if not code_match:
        raise ValueError("未识别到6位股票代码")
    code = code_match.group(1)

    amount = None
    hand_match = re.search(r"(\d+)手", compact)
    if hand_match:
        amount = int(hand_match.group(1)) * LOT_SIZE
    else:
        share_match = re.search(r"(\d+)股", compact)
        if share_match:
            amount = int(share_match.group(1))
    if amount is None:
        raise ValueError("未识别到数量，请带‘100股’或‘1手’")

    name_part = compact
    name_part = re.sub(r"^(买入|买|卖出|卖)", "", name_part)
    name_part = name_part.replace(code, "")
    name_part = re.sub(r"\d+手", "", name_part)
    name_part = re.sub(r"\d+股", "", name_part)
    name = name_part.strip()
    if not name:
        raise ValueError("未识别到股票名称")

    return preview_order(operate, code, name, amount, strategy_no)


def place_trade_text(text: str, strategy_no: str = DEFAULT_STRATEGY_NO):
    order = parse_trade_text(text, strategy_no)
    return place_order(order["operate"], order["code"], order["name"], order["amount"], order["strategy_no"], price=order.get("price"))


def normalize_order(order: Dict[str, Any]):
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

    # 根据板块规则校验申报数量
    board = get_board_info(code)
    board_name = board["name"]
    min_amount = board["min_amount"]
    amount_step = board["amount_step"]

    if amount < min_amount:
        raise ValueError(f"{board_name}股票最小申报数量为{min_amount}股，当前数量{amount}股不足")

    if amount_step > 1:
        # 主板/创业板/北交所：必须是100股整数倍
        if amount % amount_step != 0:
            raise ValueError(f"{board_name}股票委托数量必须是{amount_step}股整数倍，当前{amount}股不符合")
    else:
        # 科创板：超过200股部分可按1股递增，无需整数倍校验
        pass

    # 根据板块规则自动判断委托类型
    price = order.get("price")
    supports_market = board["market_order"]

    if not supports_market:
        # 北交所等不支持市价委托 → 强制限价委托
        order_type = "limit"
        if price is None:
            raise ValueError(f"{board_name}不支持市价委托，必须提供委托价格(price参数)")
    elif price is not None:
        # 用户指定了价格 → 限价委托
        order_type = "limit"
    else:
        # 默认市价委托
        order_type = "market"

    strategy_no = str(order.get("strategy_no", DEFAULT_STRATEGY_NO)).strip() or DEFAULT_STRATEGY_NO

    result = {
        "operate": operate,
        "code": code,
        "name": name,
        "amount": amount,
        "strategy_no": strategy_no,
        "board": board_name,
        "order_type": order_type,
    }
    if order_type == "limit":
        result["price"] = price
    return result


def _make_order(operate, code, name, amount, strategy_no, order_type="market", price=None):
    order = {
        "strategy_no": strategy_no,
        "code": code,
        "name": name,
        "ct_amount": amount,
        "operate": operate,
        "order_type": order_type,
    }
    if order_type == "limit" and price is not None:
        order["price"] = price
    return order


def _post_queue(data):
    return _post("/api/queue", data)


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
  python agent_trader.py buy   代码 名称 数量  [价格] [策略编号]
  python agent_trader.py sell  代码 名称 数量  [价格] [策略编号]
  python agent_trader.py query [策略编号]
  python agent_trader.py text  \"买江丰电子100股300666\" [策略编号]

  价格参数：不填则市价委托；填写则限价委托
  北交所(8/4开头)必须填写价格（不支持市价委托）

示例:
  python agent_trader.py buy  300666 江丰电子 100          # 市价委托
  python agent_trader.py buy  300666 江丰电子 100 25.50    # 限价委托，价格25.50
  python agent_trader.py buy  830001 北交所股 100 10.00    # 北交所必须限价
  python agent_trader.py sell 300666 江丰电子 100
  python agent_trader.py query
  python agent_trader.py text "买江丰电子1手300666"
"""

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "buy":
        code, name, amount = sys.argv[2], sys.argv[3], int(sys.argv[4])
        price = float(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5].replace('.', '', 1).isdigit() else None
        sn_idx = 6 if price is not None else 5
        sn = sys.argv[sn_idx] if len(sys.argv) > sn_idx else DEFAULT_STRATEGY_NO
        print(json.dumps(buy(code, name, amount, price=price, strategy_no=sn), ensure_ascii=False, indent=2))

    elif cmd == "sell":
        code, name, amount = sys.argv[2], sys.argv[3], int(sys.argv[4])
        price = float(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5].replace('.', '', 1).isdigit() else None
        sn_idx = 6 if price is not None else 5
        sn = sys.argv[sn_idx] if len(sys.argv) > sn_idx else DEFAULT_STRATEGY_NO
        print(json.dumps(sell(code, name, amount, price=price, strategy_no=sn), ensure_ascii=False, indent=2))

    elif cmd == "query":
        sn = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_STRATEGY_NO
        print(json.dumps(query(sn), ensure_ascii=False, indent=2))

    elif cmd == "text":
        text = sys.argv[2]
        sn = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_STRATEGY_NO
        print(json.dumps(place_trade_text(text, sn), ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {cmd}\n")
        print(usage)
