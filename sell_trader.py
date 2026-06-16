"""
独立卖出脚本。

目标：
- 只负责卖出
- 不写死股票、数量、策略编号
- 复用 agent_trader 的统一校验与执行能力

用法：
    python sell_trader.py 300666 江丰电子 100
    python sell_trader.py 601318 中国平安 200 my_strategy
    python sell_trader.py "卖出中国平安100股601318"
"""

import json
import sys

sys.path.insert(0, r"D:\ths_trade")
from agent_trader import DEFAULT_STRATEGY_NO, place_trade_text, sell


def sell_stock(code: str, name: str, amount: int, strategy_no: str = DEFAULT_STRATEGY_NO):
    return sell(code, name, amount, strategy_no)


def sell_text(text: str, strategy_no: str = DEFAULT_STRATEGY_NO):
    result = place_trade_text(text, strategy_no)
    return result


if __name__ == "__main__":
    usage = """用法:
  python sell_trader.py 代码 名称 数量 [策略编号]
  python sell_trader.py "卖出中国平安100股601318" [策略编号]

示例:
  python sell_trader.py 300666 江丰电子 100
  python sell_trader.py 601318 中国平安 200 my_strategy
  python sell_trader.py "卖出中国平安100股601318"
"""

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(0)

    if len(sys.argv) == 2 or (len(sys.argv) == 3 and ("买" in sys.argv[1] or "卖" in sys.argv[1])):
        text = sys.argv[1]
        sn = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_STRATEGY_NO
        print(json.dumps(sell_text(text, sn), ensure_ascii=False, indent=2))
        sys.exit(0)

    code, name, amount = sys.argv[1], sys.argv[2], int(sys.argv[3])
    sn = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_STRATEGY_NO
    print(json.dumps(sell_stock(code, name, amount, sn), ensure_ascii=False, indent=2))
