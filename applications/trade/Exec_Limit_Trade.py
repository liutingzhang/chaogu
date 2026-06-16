"""
限价委托执行入口
被 web server 调用，消费队列中的限价委托任务
"""

from applications.trade.server.THS_Limit_Trader_Server import THSLimitTraderServer
from applications.work_queue.ActiveWork import ActiveWork

# 限价委托专用服务实例
ths = THSLimitTraderServer()
# 活动的工作流初始化
aw = ActiveWork()


def exec_run(item):
    if item['operate'] == 'buy':
        print(f'========得到限价买入指令 {item["stock_no"]} {item["amount"]} 委托价={item.get("price", "")} ========')
        result = ths.buy(item)
        if result.get("success"):
            print("合同号:", result.get('entrust_no', ''))
        else:
            print(result.get('msg', '限价买入失败'))
        return result

    if item['operate'] == 'sell':
        print(f'========得到限价卖出指令 {item["stock_no"]} {item["amount"]} 委托价={item.get("price", "")} ========')
        result = ths.sell(item)
        if result.get("success"):
            print("合同号:", result.get('entrust_no', ''))
        else:
            print(result.get('msg', '限价卖出失败'))
        return result

    return {"success": False, "msg": f"不支持的操作: {item.get('operate')}"}


if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    item = {
        'operate': 'buy',
        'stock_no': '688262',
        'stock_name': '国芯科技',
        'amount': 200,
        'price': '35.78',
    }
    print(exec_run(item))
