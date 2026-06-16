from applications.tool.CSV_Helper import CSVHelper
import applications.trade.Exec_Auto_Trade as ExecAutoTrade
import pandas as pd

pdcsv = CSVHelper()

def searchWorkLog(item):
    # 读取工作数据记录
    dfwork = pdcsv.getCVS()
    if dfwork.empty or '策略编号' not in dfwork.columns:
        return dfwork

    # 筛选符合此条件的策略数据
    dfwork = dfwork.astype({'策略编号': 'str'})
    dfwork = dfwork[dfwork['策略编号'] == str(item['strategy_no'])]
    if dfwork.empty:
        return dfwork

    # 再次查找市价委托得到数据集
    dfgrid = ExecAutoTrade.exec_run(item)
    if dfgrid is None or not isinstance(dfgrid, pd.DataFrame) or dfgrid.empty:
        return dfwork
    if '合同编号' not in dfgrid.columns:
        print('查询结果缺少 合同编号 列，跳过本次匹配')
        return dfwork

    dfgrid = dfgrid.astype({'合同编号': 'str'})
    if '合同编号' in dfwork.columns:
        dfwork = dfwork.astype({'合同编号': 'str'})

    # 对合同号不为0的记录进行状态更新
    for workrow in dfwork.iterrows():
        contract_no = str(workrow[1].get('合同编号', '0'))
        if contract_no == '0':
            continue
        matched = dfgrid[dfgrid['合同编号'] == contract_no]
        if matched.empty:
            continue
        gridrow = matched.iloc[0]
        if '备注' in gridrow.index:
            dfwork.loc[dfwork['合同编号'] == contract_no, '备注'] = str(gridrow['备注'])
    return dfwork
