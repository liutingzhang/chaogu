"""
独立撤单脚本。

目标：
- 只负责撤销委托
- 不写死合同编号、策略编号
- 复用 agent_trader 的公共接口

用法：
    python cancel_trader.py 6040023978
    python cancel_trader.py 6040023978 my_strategy
"""

import json
import sys

sys.path.insert(0, r"D:\ths_trade")
from agent_trader import DEFAULT_STRATEGY_NO, cancel


if __name__ == "__main__":
    usage = """用法:
  python cancel_trader.py 合同编号 [策略编号]

示例:
  python cancel_trader.py 6040023978
  python cancel_trader.py 6040023978 my_strategy
"""

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(0)

    entrust_no = sys.argv[1]
    strategy_no = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_STRATEGY_NO
    print(json.dumps(cancel(entrust_no, strategy_no), ensure_ascii=False, indent=2))
