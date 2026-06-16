from threading import Timer
from applications.work_queue.ActiveWork import ActiveWork
import applications.Global_Var_Model as gl
import datetime
import time
import applications.trade.Exec_Auto_Trade as ExecAutoTrade
import applications.trade.Exec_Limit_Trade as ExecLimitTrade
import sys
sys.path.append(r'')
from applications import API_Config

# 活动的工作流初始化
aw = ActiveWork()

def search_item_exec():
    """ 只执行队列中的买卖任务，不做查询同步 """
    executed = False
    while True:
        item = aw.get_Queue_the_one()
        if item is None:
            if not executed:
                pending = 0
                if gl.gl_queue_DF_Data is not None and not gl.gl_queue_DF_Data.empty and 'status' in gl.gl_queue_DF_Data.columns:
                    pending = len(gl.gl_queue_DF_Data[gl.gl_queue_DF_Data['status'] == 0])
                if pending > 0:
                    print("当前无可执行任务，待执行数量:", pending)
            break
        executed = True
        print("准备执行任务:", item.get('operate'), item.get('stock_no'), item.get('key'))

        # 根据 order_type 分发到市价委托或限价委托执行器
        order_type = str(item.get('order_type', 'market')).strip().lower()
        if order_type == 'limit':
            ExecLimitTrade.exec_run(item)
        else:
            ExecAutoTrade.exec_run(item)

        if 'key' in item:
            aw.edit_queue_the_one_status(item['key'])
    gl.gl_is_working = False

def auto_trade(interval):
    """ 执行自动化交易：只消费队列，不做委托查询和日志同步 """
    if gl.gl_is_working:
        return

    gl.gl_is_working = True
    search_item_exec()

    time_start = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '00:00', '%Y-%m-%d%H:%M')
    time_end = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '00:03', '%Y-%m-%d%H:%M')
    n_time = datetime.datetime.now()
    if n_time > time_start and n_time < time_end:
        gl.gl_queue_DF_Data.drop(gl.gl_queue_DF_Data.index, inplace=True)
        gl.gl_queue_DF_Data = gl.gl_queue_DF_Data.loc[:, API_Config.cfg['activework_field']]
        gl.gl_queue_DF_Data.to_csv(API_Config.cfg["activework_path"], sep='\t', index=False)
        print("==================================================")
        print("======↓↓↓↓↓", datetime.datetime.now(), "↓↓↓↓↓======")
        print("==================================================")

    t = Timer(interval, auto_trade, (interval,))
    t.start()

# 定时器 定时调用
t_exec = Timer(2, auto_trade, (2,))
t_exec.start()







