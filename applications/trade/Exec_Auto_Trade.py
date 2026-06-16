
from applications.trade.server.THS_Trader_Server import THSTraderServer
from applications.work_queue.ActiveWork import ActiveWork

# 市价委托交易初始化
ths = THSTraderServer()
# 活动的工作流初始化
aw = ActiveWork()


def exec_run(item):
    """ 市价委托执行入口（仅处理市价委托，限价委托走 Exec_Limit_Trade）"""

    if item['operate'] == 'buy':
        print(f'========得到市价买入指令 {item["stock_no"]} {item["amount"]} ========')
        result = ths.buy(item)
        if result.get("auto") and result.get('success'):
            print("合同号:", result.get('entrust_no', ''))
        else:
            print(result.get('msg', '买入失败'))
        return result

    if item['operate'] == 'sell':
        print(f'========得到市价卖出指令 {item["stock_no"]} {item["amount"]} ========')
        result = ths.sell(item)
        if result.get("auto") and result.get('success'):
            print("合同号:", result.get('entrust_no', ''))
        else:
            print(result.get('msg', '卖出失败'))
        return result

    if item['operate'] == 'cancel':
        print('========得到撤单指令', item['stock_no'])
        result = ths.cancel(item)
        if result.get("auto") and result.get('success'):
            print("撤单合同号:", result.get('entrust_no', ''))
        else:
            print(result.get('msg', '撤单失败'))
        return result

    if item['operate'] == 'get_position':
        return ths.get_position()

    if item['operate'] == 'get_today_trades':
        return ths.get_today_trades()

    if item['operate'] == 'get_today_entrusts':
        return ths.get_today_entrusts()

    if item['operate'] == 'get_balance':
        return ths.get_balance()

    if 'key' in item:
        aw.edit_queue_the_one_status(item['key'])
