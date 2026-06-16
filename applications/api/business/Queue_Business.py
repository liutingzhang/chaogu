
from common.CommonHandler import CommonHandler
from trest.router import post
import json
import pandas as pd
from pandas import json_normalize
import applications.Global_Var_Model as gl
import applications.trade.Search_Work_Log as SearchWorkLog
import uuid
import time
from applications import API_Config


def InputQueue(_json):
    """ 输入一个dataframe 加入队列中 """
    data_list = json.loads(_json)
    if isinstance(data_list, str):
        data_list = json.loads(data_list)

    for item in data_list:
        item["stock_no"] = str(item["code"]).split('.')[0]
        item["stock_name"] = str(item["name"])
        item["amount"] = str(item.get("ct_amount", item.get("amount", "")))
        item["order_type"] = str(item.get("order_type", "market"))
        item["price"] = str(item.get("price", ""))
        item["key"] = str(uuid.uuid1())
        item["status"] = 0

    df_1 = json_normalize(data_list)
    df = df_1.loc[:, API_Config.cfg['activework_field']]

    if gl.gl_queue_DF_Data is None:
        try:
            gl.gl_queue_DF_Data = pd.read_csv(API_Config.cfg['activework_path'], sep='\t')
        except Exception:
            gl.gl_queue_DF_Data = pd.DataFrame(columns=API_Config.cfg['activework_field'])

    if gl.gl_queue_DF_Data.empty:
        gl.gl_queue_DF_Data = pd.DataFrame(columns=API_Config.cfg['activework_field'])
    else:
        missing_fields = [field for field in API_Config.cfg['activework_field'] if field not in gl.gl_queue_DF_Data.columns]
        for field in missing_fields:
            gl.gl_queue_DF_Data[field] = ''
        gl.gl_queue_DF_Data = gl.gl_queue_DF_Data.loc[:, API_Config.cfg['activework_field']]

    gl.gl_queue_DF_Data = pd.concat([gl.gl_queue_DF_Data, df], ignore_index=True)
    gl.gl_queue_DF_Data = gl.gl_queue_DF_Data.loc[:, API_Config.cfg['activework_field']]
    gl.gl_queue_DF_Data.to_csv(API_Config.cfg['activework_path'], sep='\t', index=False)
    print("入队成功，新增数量:", len(df), "当前队列总数:", len(gl.gl_queue_DF_Data))

def SearchData(_json):

    """ 查询结果 """
    i = 0
    # 检测是否再干活 如果在干活则等待0.5秒  共等待300次
    while i <= 300:
        if gl.gl_is_working:
            time.sleep(API_Config.cfg["sleepB"])
        else:
            gl.gl_is_working = True  # 设置自动化交易正在进行中
            gl.gl_is_searching = True  # 设定查询中的全局变量正在工作
            # 接收到新的指令时加入到dataframe中 并存储一份
            item = json.loads(_json)  # 字符串转json
            # 传入的策略号返回数据集
            df = SearchWorkLog.searchWorkLog(item)
            resJSON = df.to_dict('records')
            # 返回结果集
            # resJSON = {'fff': 'aaaa', 'name': 'bb'}
            i = 1000
        i += 1
    gl.gl_is_working = False  # 干完活设置空闲状态
    gl.gl_is_searching = False  # 设定查询中的全局变量正在工作
    return resJSON
