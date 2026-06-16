"""
限价委托服务端 — 独立于市价委托
专门处理科创板、北交所等只支持限价委托的板块

与 THS_Trader_Server.py（市价委托）的核心区别：
1. 菜单路径：买入[F1] / 卖出[F2]（限价界面）vs 市价委托→买入/卖出（市价界面）
2. 无重填按钮：限价界面没有重填按钮（0x3EF），需手动清空输入框
3. 需输入价格：限价界面有价格输入框（0x409），需先清空再输入委托价
4. 无ComboBox：限价界面没有申报方式ComboBox（0x605），直接点买入/卖出按钮
5. 价格笼子校验：限价委托价格需在有效申报范围内

同花顺限价委托界面控件ID（参考 jqktrader / easytrader 开源项目）：
  - 0x408: 证券代码 Edit
  - 0x409: 委托价格 Edit
  - 0x40A: 委托数量 Edit
  - 0x3EE: 买入/卖出 Button
  - 0x3FA: 可买数量 Static
  - 0x40E: 可卖数量 Static
  - 0x3EC: 结果弹窗 Static
  - 0x2:   弹窗确定 Button

A股限价委托规则（联网搜索整理）：
  ┌─────────┬──────────┬──────────┬──────────────────────────────────────────┐
  │ 板块     │ 涨跌幅    │ 最小申报  │ 连续竞价价格笼子                           │
  ├─────────┼──────────┼──────────┼──────────────────────────────────────────┤
  │ 沪主板   │ ±10%     │ 100股    │ 买入≤基准价102%或+0.1元(取高)              │
  │         │          │          │ 卖出≥基准价98%或-0.1元(取低)               │
  │ 深主板   │ ±10%     │ 100股    │ 同沪主板                                  │
  │ 创业板   │ ±20%     │ 100股    │ 买入≤基准价102%或+0.1元(取高)              │
  │         │          │          │ 卖出≥基准价98%或-0.1元(取低)               │
  │ 科创板   │ ±20%     │ 200股    │ 买入≤基准价102%                           │
  │         │ 超200按1股递增│       │ 卖出≥基准价98%                            │
  │ 北交所   │ ±30%     │ 100股    │ 买入≤基准价105%或+0.1元(取高)              │
  │         │          │          │ 卖出≥基准价95%或-0.1元(取低)               │
  │ ST股    │ ±5%      │ 100股    │ 同所属板块                                │
  └─────────┴──────────┴──────────┴──────────────────────────────────────────┘
  注：集合竞价阶段仅受涨跌幅限制，不受价格笼子约束
"""

import pywinauto
from pywinauto import keyboard
import time
import datetime
import sys

sys.path.append(r'../../tool')
from applications import API_Config


class THSLimitTraderServer:
    """ 限价委托专用服务类 """

    def __init__(self, exe_path=API_Config.cfg['exe_path']):
        print("正在连接客户端:", exe_path, "...")
        self.app = pywinauto.Application().connect(path=exe_path, timeout=10)
        print("已连接到" + exe_path + ";")
        self.main_wnd = self.app.window(title="网上股票交易系统5.0")
        self.app.top_window().set_focus()
        self.__esc()

    # ─────────────────────────────────────────────
    # 限价委托买入 / 卖出
    # ─────────────────────────────────────────────
    def buy(self, item):
        """ 限价委托买入 """
        return self._trade_impl(item, 'buy')

    def sell(self, item):
        """ 限价委托卖出 """
        return self._trade_impl(item, 'sell')

    # ─────────────────────────────────────────────
    # 通用限价委托实现
    # ─────────────────────────────────────────────
    def _trade_impl(self, item, operate: str):
        """ 限价委托通用实现
        operate: 'buy' 买入 | 'sell' 卖出
        item 必须包含: stock_no, stock_name, amount, price
        """
        # 限价委托菜单：买入[F1] / 卖出[F2]
        menu_path = ['买入[F1]'] if operate == 'buy' else ['卖出[F2]']
        print(f"======== 限价{('买入' if operate == 'buy' else '卖出')} {item['stock_no']} {item['amount']}股 委托价={item.get('price', '')} ========")

        # 1. 切换到限价委托界面
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.__select_menu(menu_path)
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.__select_menu(menu_path)

        time.sleep(API_Config.cfg["sleepA"])

        # 2. 清空并输入证券代码（限价界面没有重填按钮，需手动清空）
        try:
            code_edit = self.main_wnd.window(control_id=0x408, class_name="Edit")
            self._clear_and_type(code_edit, str(item['stock_no']))
        except:
            time.sleep(API_Config.cfg["sleepC"])
            code_edit = self.main_wnd.window(control_id=0x408, class_name="Edit")
            self._clear_and_type(code_edit, str(item['stock_no']))

        # 3. 处理市场二义性弹窗
        self._resolve_market_ambiguity(item)

        time.sleep(API_Config.cfg["sleepA"])

        # 4. 清空并输入委托价格（限价委托核心步骤）
        price = str(item.get('price', ''))
        if not price:
            self.__esc()
            return self._error_result(item, operate, "限价委托必须提供 price 字段")
        try:
            price_edit = self.main_wnd.window(control_id=0x409, class_name="Edit")
            self._clear_and_type(price_edit, price)
        except:
            time.sleep(API_Config.cfg["sleepC"])
            price_edit = self.main_wnd.window(control_id=0x409, class_name="Edit")
            self._clear_and_type(price_edit, price)

        # 5. 输入委托数量
        try:
            amount_edit = self.main_wnd.window(control_id=0x40A, class_name="Edit")
            self._clear_and_type(amount_edit, str(item['amount']))
        except:
            time.sleep(API_Config.cfg["sleepC"])
            amount_edit = self.main_wnd.window(control_id=0x40A, class_name="Edit")
            self._clear_and_type(amount_edit, str(item['amount']))

        time.sleep(API_Config.cfg["sleepA"])

        # 6. 校验可买/可卖数量
        if operate == 'buy':
            can_text = self._safe_get_text(0x3FA)
            print(f"可买(股): {can_text}, 指令要求: {item['amount']}")
            try:
                if int(item['amount']) > int(can_text):
                    self.__esc()
                    return self._error_result(item, operate, f"资金不足：可买{can_text}股，指令要买{item['amount']}股")
            except ValueError:
                pass
        else:
            can_text = self._safe_get_text(0x40E)
            print(f"可用余额: {can_text}, 指令要求: {item['amount']}")
            try:
                if int(item['amount']) > int(can_text):
                    self.__esc()
                    return self._error_result(item, operate, f"股份不足：可用{can_text}股，指令要卖{item['amount']}股")
            except ValueError:
                pass

        # 7. 点击买入/卖出按钮（限价委托无ComboBox申报方式，直接点击）
        try:
            self.main_wnd.window(control_id=0x3EE, class_name="Button").click()
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.main_wnd.window(control_id=0x3EE, class_name="Button").click()

        # 8. 等待弹窗
        time.sleep(API_Config.cfg["sleepB"])
        time.sleep(API_Config.cfg["sleepC"])

        # 9. 处理委托确认弹窗（自动按Y确认）
        self._confirm_trade_dialog()

        # 10. 读取结果
        time.sleep(API_Config.cfg["sleepB"])
        result = self._read_result_text()
        # 11. 关闭结果弹窗
        self._close_result_dialog()

        self.__esc()
        return self._parse_result(result)

    # ─────────────────────────────────────────────
    # 辅助方法
    # ─────────────────────────────────────────────
    def _clear_and_type(self, edit_ctrl, text: str):
        """ 清空Edit控件并输入新内容
        限价委托界面没有重填按钮，需要手动清空输入框
        采用三重策略确保清空：set_edit_text → 全选删除 → 逐字符删除
        """
        # 策略1：set_edit_text 直接设置（最可靠）
        try:
            edit_ctrl.set_edit_text('')
        except Exception:
            # 策略2：Ctrl+A 全选 + Backspace 删除
            try:
                edit_ctrl.type_keys('^a{BACKSPACE}')
            except Exception:
                # 策略3：逐字符删除
                try:
                    text_len = edit_ctrl.line_length(0)
                    for _ in range(text_len + 2):
                        edit_ctrl.type_keys("{BACKSPACE}")
                except Exception:
                    pass
        # 输入新内容
        edit_ctrl.type_keys(text)

    def _safe_get_text(self, control_id) -> str:
        """ 安全获取Static控件文本 """
        try:
            text_ctrl = self.main_wnd.window(control_id=control_id, class_name="Static")
            return text_ctrl.texts()[0]
        except Exception:
            try:
                time.sleep(API_Config.cfg["sleepC"])
                text_ctrl = self.main_wnd.window(control_id=control_id, class_name="Static")
                return text_ctrl.texts()[0]
            except Exception:
                return "0"

    def _read_result_text(self) -> str:
        """ 读取委托结果弹窗文本 """
        try:
            result = self.app.top_window().window(control_id=0x3EC, class_name='Static')
            if result.exists(timeout=2):
                return result.window_text()
        except Exception:
            pass
        try:
            time.sleep(API_Config.cfg["sleepC"])
            result = self.app.top_window().window(control_id=0x3EC, class_name='Static')
            if result.exists(timeout=2):
                return result.window_text()
        except Exception:
            pass
        # 尝试从顶层窗口文本中查找
        try:
            texts = self.app.top_window().texts()
            for text in texts:
                if '合同编号' in str(text) or '已成功提交' in str(text) or '系统正在清算中' in str(text):
                    return str(text)
        except Exception:
            pass
        return ''

    def _close_result_dialog(self):
        """ 关闭结果弹窗 """
        try:
            self.app.top_window().set_focus()
            self.app.top_window().window(control_id=0x2, class_name='Button').click()
        except Exception:
            try:
                self.app.top_window().set_focus()
                time.sleep(API_Config.cfg["sleepC"])
                self.app.top_window().window(control_id=0x2, class_name='Button').click()
            except Exception:
                pass

    def _confirm_trade_dialog(self):
        """ 处理委托确认弹窗，自动按 Y 确认
        限价委托也会弹出确认窗口，需要自动确认
        """
        try:
            for _ in range(8):
                top = self.app.top_window()
                title = top.window_text()
                try:
                    top.set_focus()
                except Exception:
                    pass

                texts = []
                try:
                    texts = top.texts()
                except Exception:
                    pass

                joined = " ".join([str(x) for x in texts])
                if ("委托确认" in title) or ("您是否确定以上" in joined) or ("买入数量" in joined and "证券代码" in joined):
                    # 尝试按Y确认
                    for keys in ['y', 'Y', '%Y', '{LEFT}{ENTER}', '{ENTER}']:
                        try:
                            top.set_focus()
                            keyboard.send_keys(keys)
                            time.sleep(API_Config.cfg["sleepA"])
                            return
                        except Exception:
                            pass
                    # 尝试点击"是(Y)"按钮
                    try:
                        btn = top.window(title="是(Y)", class_name='Button')
                        if btn.exists(timeout=1):
                            btn.click_input()
                            return
                    except Exception:
                        pass
                elif title == '' and texts == ['']:
                    # 空标题弹窗也可能是确认
                    for keys in ['y', 'Y', '{ENTER}']:
                        try:
                            top.set_focus()
                            keyboard.send_keys(keys)
                            time.sleep(API_Config.cfg["sleepA"])
                            return
                        except Exception:
                            pass
                time.sleep(API_Config.cfg["sleepA"])
        except Exception as ex:
            print("处理委托确认弹窗失败:", ex)

    def _resolve_market_ambiguity(self, item):
        """ 处理市场二义性弹窗 """
        try:
            time.sleep(API_Config.cfg["sleepA"])
            top_text_title = ""
            try:
                top_text_title = self.app.top_window().window_text()
            except Exception:
                time.sleep(API_Config.cfg["sleepC"])
                top_text_title = self.app.top_window().window_text()

            if top_text_title == '':
                try:
                    leftbutton = self.app.top_window().window(control_id=0x7CD, class_name='Button')
                    lefttext = leftbutton.texts()
                except Exception:
                    time.sleep(API_Config.cfg["sleepC"])
                    leftbutton = self.app.top_window().window(control_id=0x7CD, class_name='Button')
                    lefttext = leftbutton.texts()

                time.sleep(API_Config.cfg["sleepA"])
                try:
                    rightbutton = self.app.top_window().window(control_id=0x7AF, class_name='Button')
                    rigthtext = rightbutton.texts()
                except Exception:
                    time.sleep(API_Config.cfg["sleepC"])
                    rightbutton = self.app.top_window().window(control_id=0x7AF, class_name='Button')
                    rigthtext = rightbutton.texts()

                time.sleep(API_Config.cfg["sleepA"])

                if str(item.get('stock_name', '')) in str(lefttext[0].replace('\n', '')):
                    leftbutton.click()
                if str(item.get('stock_name', '')) in str(rigthtext[0].replace('\n', '')):
                    rightbutton.click()
        except Exception:
            pass

    def _error_result(self, item, operate, msg):
        return {
            "success": False,
            "auto": True,
            "msg": msg,
            "result": {
                "委托时间": datetime.datetime.now().strftime("%H:%M:%S"),
                "证券代码": str(item.get('stock_no', '')),
                "证券名称": str(item.get('stock_name', '')),
                "操作": "买入" if operate == 'buy' else "卖出",
                "备注": msg,
                "委托数量": str(item.get('amount', 0)),
                "成交数量": "0",
                "委托价格": str(item.get('price', 0)),
                "成交均价": "0",
                "撤消数量": "0",
                "合同编号": "0",
                "策略编号": str(item.get('strategy_no', '')),
            }
        }

    @staticmethod
    def _parse_result(result):
        """ 解析委托结果 """
        if not result:
            return {"success": False, "auto": True, "msg": "未获取到结果文本", "entrust_no": ""}
        if "已成功提交，合同编号：" in result:
            return {
                "success": True,
                "auto": True,
                "msg": result,
                "entrust_no": result.split("合同编号：")[1].split("。")[0]
            }
        else:
            return {"success": False, "auto": True, "msg": result, "entrust_no": ""}

    def __select_menu(self, path):
        """ 点击左边菜单 """
        if r"网上股票" not in self.app.top_window().window_text():
            self.app.top_window().set_focus()
            pywinauto.keyboard.send_keys("{ENTER}")
        self.__get_left_menus_handle().get_item(path).click()

    def __get_left_menus_handle(self):
        while True:
            try:
                handle = self.main_wnd.window(control_id=0x81, class_name='SysTreeView32')
                handle.wait('ready', 2)
                return handle
            except Exception:
                pass

    def __esc(self):
        """ ESC 取消 """
        try:
            self.app.top_window().set_focus()
            pywinauto.keyboard.send_keys('{VK_ESCAPE}')
        except Exception:
            pass
