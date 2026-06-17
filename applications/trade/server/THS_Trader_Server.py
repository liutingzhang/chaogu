import pywinauto
from pywinauto import clipboard, keyboard
import pandas as pd
import io
import time
import datetime
import sys

sys.path.append(r'../../tool')
from applications import API_Config


class THSTraderServer:

    def __init__(self, exe_path=API_Config.cfg['exe_path']):  # r"C:\同花顺软件\同花顺\xiadan.exe"
        # print(api_config.cfg['exe_path'])
        print("正在连接客户端:", exe_path, "...")
        self.app = pywinauto.Application().connect(path=exe_path, timeout=10)
        print("已连接到" + exe_path + ";")
        self.main_wnd = self.app.window(title="网上股票交易系统5.0")  # self.app.top_window()
        self.app.top_window().set_focus()
        self.__esc()

    # ─────────────────────────────────────────────
    # 市价委托买入 / 卖出（仅市价委托，限价委托走 THS_Limit_Trader_Server）
    # ─────────────────────────────────────────────
    def buy(self, item):
        """ 市价委托买入 """
        return self._buy_impl(item)

    def sell(self, item):
        """ 市价委托卖出 """
        return self._sell_impl(item)

    # ─────────────────────────────────────────────
    # 通用买入实现（市价委托专用）
    # ─────────────────────────────────────────────
    def _buy_impl(self, item):
        """ 市价买入实现 """
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.__select_menu(['市价委托', '买入'])
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.__select_menu(['市价委托', '买入'])

        time.sleep(API_Config.cfg["sleepA"])

        try:
            self.app.top_window().window(control_id=0x3EF, class_name='Button').click()  # 重填按钮
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.app.top_window().window(control_id=0x3EF, class_name='Button').click()  # 重填按钮

        time.sleep(API_Config.cfg["sleepA"])

        try:
            # 设置股票代码：先点击输入框获取焦点，再输入，避免按键被键盘精灵捕获加入自选股
            code_edit = self.main_wnd.window(control_id=0x408, class_name="Edit")
            code_edit.click()
            time.sleep(0.2)
            code_edit.type_keys(str(item['stock_no']))
        except:
            time.sleep(API_Config.cfg["sleepC"])
            code_edit = self.main_wnd.window(control_id=0x408, class_name="Edit")
            code_edit.click()
            time.sleep(0.2)
            code_edit.type_keys(str(item['stock_no']))

        # 判断是否存在市场的二义性
        self._resolve_market_ambiguity(item)

        time.sleep(API_Config.cfg["sleepA"])

        try:
            amount_edit = self.main_wnd.window(control_id=0x40A, class_name="Edit")
            amount_edit.click()
            time.sleep(0.2)
            amount_edit.type_keys(str(item['amount']))  # 设置股数目
        except:
            time.sleep(API_Config.cfg["sleepC"])
            amount_edit = self.main_wnd.window(control_id=0x40A, class_name="Edit")
            amount_edit.click()
            time.sleep(0.2)
            amount_edit.type_keys(str(item['amount']))  # 设置股数目

        time.sleep(API_Config.cfg["sleepA"])
        text = ""
        try:
            text = self.main_wnd.window(control_id=0x3FA, class_name="Static")  # 可买数量
        except:
            time.sleep(API_Config.cfg["sleepC"])
            text = self.main_wnd.window(control_id=0x3FA, class_name="Static")  # 可买数量

        time.sleep(API_Config.cfg["sleepA"])
        can_buy = text.texts()  # window_text()

        # 如果可买数量为空，重试读取
        retry_count = 0
        while (not can_buy or can_buy[0].strip() == '') and retry_count < 3:
            time.sleep(API_Config.cfg["sleepC"])
            try:
                text = self.main_wnd.window(control_id=0x3FA, class_name="Static")
                can_buy = text.texts()
            except:
                pass
            retry_count += 1

        print('买入操作: 可买(股):', can_buy[0] if can_buy else '', "指令要求:", item['amount'])

        # 如果重试后仍为空，返回错误
        if not can_buy or can_buy[0].strip() == '':
            self.__esc()
            return {
                "success": False,
                "auto": False,
                "msg": "无法读取可买数量",
                "result": {
                    "委托时间": datetime.datetime.now().strftime("%H:%M:%S"),
                    "证券代码": str(item['stock_no']),
                    "证券名称": "",
                    "操作": "买入",
                    "备注": "读取可买数量为空，可能同花顺窗口未就绪",
                    "委托数量": str(item['amount']),
                    "成交数量": "0",
                    "委托价格": "0",
                    "成交均价": "0",
                    "撤消数量": "0",
                    "合同编号": "0",
                    "策略编号": "",
                }
            }

        # 判断如果指令要求的数量超过可买数量则返回创建的失败对象
        if (int(item['amount']) > int(can_buy[0])) | ((int(item['amount']) % 100) > 0):
            remark1 = "资金不足:资金可用数不足,现可买" + str(can_buy[0]) + ",指令要买" + str(item['amount'])
            remark2 = "不可拆买:委托数量必须是每手股(张)数的倍数,指令要买" + str(item['amount'])
            remark = ""
            if int(item['amount']) > int(can_buy[0]):
                remark = remark1

            if (int(item['amount']) % 100) > 0:
                remark = remark2
            self.__esc()
            return {
                "success": False,
                "auto": False,
                "msg": "自动化执行程序拦截到错误",
                "result": {
                    "委托时间": datetime.datetime.now().strftime("%H:%M:%S"),
                    "证券代码": str(item['stock_no']),
                    "证券名称": "",
                    "操作": "买入",
                    "备注": remark,
                    "委托数量": str(item['amount']),
                    "成交数量": "0",
                    "委托价格": "0",
                    "成交均价": "0",
                    "撤消数量": "0",
                    "合同编号": "0",
                    "策略编号": "",
                }
            }

        result = self.__trade()
        self.__esc()
        return result

    # ─────────────────────────────────────────────
    # 通用卖出实现（市价委托专用）
    # ─────────────────────────────────────────────
    def _sell_impl(self, item):
        """ 市价卖出实现 """
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.__select_menu(['市价委托', '卖出'])
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.__select_menu(['市价委托', '卖出'])

        time.sleep(API_Config.cfg["sleepA"])

        try:
            self.app.top_window().window(control_id=0x3EF, class_name='Button').click()  # 重填按钮
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.app.top_window().window(control_id=0x3EF, class_name='Button').click()  # 重填按钮

        time.sleep(API_Config.cfg["sleepA"])

        # 设置股票代码
        try:
            code_edit = self.main_wnd.window(control_id=0x408, class_name="Edit")
            code_edit.click()
            time.sleep(0.2)
            code_edit.type_keys(str(item['stock_no']))
        except:
            time.sleep(API_Config.cfg["sleepC"])
            code_edit = self.main_wnd.window(control_id=0x408, class_name="Edit")
            code_edit.click()
            time.sleep(0.2)
            code_edit.type_keys(str(item['stock_no']))

        # 判断是否存在市场的二义性
        self._resolve_market_ambiguity(item)

        time.sleep(API_Config.cfg["sleepA"])

        # 设置股数目
        try:
            amount_edit = self.main_wnd.window(control_id=0x40A, class_name="Edit")
            amount_edit.click()
            time.sleep(0.2)
            amount_edit.type_keys(str(item['amount']))
        except:
            time.sleep(API_Config.cfg["sleepC"])
            amount_edit = self.main_wnd.window(control_id=0x40A, class_name="Edit")
            amount_edit.click()
            time.sleep(0.2)
            amount_edit.type_keys(str(item['amount']))

        time.sleep(API_Config.cfg["sleepA"])
        text = ""
        try:
            text = self.main_wnd.window(control_id=0x40E, class_name="Static")
        except:
            time.sleep(API_Config.cfg["sleepC"])
            text = self.main_wnd.window(control_id=0x40E, class_name="Static")

        time.sleep(API_Config.cfg["sleepA"])
        can_sell = text.texts()  # window_text()
        print("卖出操作: 可用余额:", can_sell[0], "指令要求:", item['amount'])

        # 判断如果指令要求的数量超过可卖数量则返回创建的失败对象
        if (int(item['amount']) > int(can_sell[0])) | ((int(item['amount']) % 100) > 0):
            remark1 = "股份不足:股份可用数不足,现可用" + str(can_sell[0]) + "指令要卖" + str(item['amount'])
            remark2 = "不可拆卖:不允许将整股拆成零股来卖,指令要卖" + str(item['amount'])
            remark = "自动化执行程序拦截到错误"
            if int(item['amount']) > int(can_sell[0]):
                remark = remark1

            if (int(item['amount']) % 100) > 0:
                remark = remark2
            self.__esc()
            return {
                "success": False,
                "auto": False,
                "msg": "股份可用数不足",
                "result": {
                    "委托时间": datetime.datetime.now().strftime("%H:%M:%S"),
                    "证券代码": str(item['stock_no']),
                    "证券名称": "",
                    "操作": "卖出",
                    "备注": remark,
                    "委托数量": str(item['amount']),
                    "成交数量": "0",
                    "委托价格": "0",
                    "成交均价": "0",
                    "撤消数量": "0",
                    "合同编号": "0",
                    "策略编号": "",
                }
            }

        result = self.__trade()
        self.__esc()
        return result

    # ─────────────────────────────────────────────
    # 市场二义性处理（提取公共逻辑）
    # ─────────────────────────────────────────────
    def _resolve_market_ambiguity(self, item):
        """判断是否存在市场的二义性并自动选择"""
        try:
            time.sleep(API_Config.cfg["sleepA"])
            top_text_title = ""
            try:
                top_text_title = self.app.top_window().window_text()
            except:
                time.sleep(API_Config.cfg["sleepC"])
                top_text_title = self.app.top_window().window_text()

            if top_text_title == '':
                try:
                    leftbutton = self.app.top_window().window(control_id=0x7CD, class_name='Button')
                    lefttext = leftbutton.texts()
                except:
                    time.sleep(API_Config.cfg["sleepC"])
                    leftbutton = self.app.top_window().window(control_id=0x7CD, class_name='Button')
                    lefttext = leftbutton.texts()

                time.sleep(API_Config.cfg["sleepA"])
                try:
                    rightbutton = self.app.top_window().window(control_id=0x7AF, class_name='Button')
                    rigthtext = rightbutton.texts()
                except:
                    time.sleep(API_Config.cfg["sleepC"])
                    rightbutton = self.app.top_window().window(control_id=0x7AF, class_name='Button')
                    rigthtext = rightbutton.texts()

                time.sleep(API_Config.cfg["sleepA"])

                if str(item['stock_name']) in str(lefttext[0].replace('\n', '')):
                    leftbutton.click()
                if str(item['stock_name']) in str(rigthtext[0].replace('\n', '')):
                    rightbutton.click()
        except:
            pass

    def cancel(self, item):
        """ 撤单：F3 后输入证券代码，选中第一行，再按 x / y """
        stock_no = str(item['stock_no']).strip()
        print("进入撤单流程(F3查询代码路径), 证券代码:", stock_no)
        self.app.top_window().set_focus()
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.__select_menu(['撤单[F3]'])
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.__select_menu(['撤单[F3]'])

        time.sleep(API_Config.cfg["sleepA"])

        try:
            code_edit = self.main_wnd.window(control_id=0x408, class_name="Edit")
            code_edit.set_focus()
            try:
                code_edit.set_edit_text('')
            except Exception:
                keyboard.send_keys('^a{BACKSPACE}')
            time.sleep(API_Config.cfg["sleepA"])
            code_edit.type_keys(stock_no)
            print("撤单页已输入证券代码:", stock_no)
        except Exception as ex:
            print("撤单页控件输入失败，改用键盘聚焦查询框:", ex)
            try:
                self.app.top_window().set_focus()
                time.sleep(API_Config.cfg["sleepA"])
                for _ in range(6):
                    keyboard.send_keys('{TAB}')
                    time.sleep(0.05)
                keyboard.send_keys('^a{BACKSPACE}')
                time.sleep(API_Config.cfg["sleepA"])
                keyboard.send_keys(stock_no)
                print("撤单页已通过键盘输入证券代码:", stock_no)
            except Exception as ex2:
                self.__esc()
                return {
                    "success": False,
                    "auto": True,
                    "msg": f"撤单页输入证券代码失败: {ex2}"
                }

        time.sleep(API_Config.cfg["sleepB"])
        if not self.__activate_cancel_target(0):
            self.__esc()
            return {
                "success": False,
                "auto": True,
                "msg": f"已输入证券代码 {stock_no}，但未能选中首条委托"
            }

        time.sleep(API_Config.cfg["sleepA"])
        if not self.__trigger_cancel_action():
            self.__esc()
            return {
                "success": False,
                "auto": True,
                "msg": f"已选中证券代码 {stock_no}，但未能触发撤单操作"
            }

        print("开始确认撤单弹窗")
        time.sleep(API_Config.cfg["sleepB"])
        self.__confirm_trade_dialog()
        time.sleep(API_Config.cfg["sleepC"])
        result = self.__read_trade_result_text()
        print("撤单结果文本:", result)
        self.__close_result_dialog()
        self.__esc()
        return self.__parse_result(result)

    def get_balance(self):
        """ 获取资金情况 """
        self.app.top_window().set_focus()
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.__select_menu(['查询[F4]', '资金明细'])
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.__select_menu(['查询[F4]', '资金明细'])

        time.sleep(API_Config.cfg["sleepB"])
        df = self.__get_grid_data()
        self.__esc()
        return df

    def get_position(self):
        """ 获取市价委托的F6持仓 """
        self.app.top_window().set_focus()
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.__select_menu(['市价委托', '卖出'])
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.__select_menu(['市价委托', '卖出'])

        time.sleep(API_Config.cfg["sleepB"])
        keyboard.send_keys('{VK_F6}')  # 点击持仓选项卡
        self.__click_update_button()
        time.sleep(API_Config.cfg["sleepA"])
        df = self.__get_grid_data()
        self.__esc()
        return df

    def get_today_trades(self):
        """ 获取市价委托的F7当日成交"""
        self.app.top_window().set_focus()
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.__select_menu(['市价委托', '卖出'])
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.__select_menu(['市价委托', '卖出'])

        time.sleep(API_Config.cfg["sleepB"])
        keyboard.send_keys('{VK_F7}')  # 点击成交选项卡
        self.__click_update_button()
        time.sleep(API_Config.cfg["sleepA"])
        df = self.__get_grid_data()
        self.__esc()
        return df

    def get_today_entrusts(self):
        """ 获取市价委托的F8委托 """
        self.app.top_window().set_focus()
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.__select_menu(['市价委托', '卖出'])
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.__select_menu(['市价委托', '卖出'])

        time.sleep(API_Config.cfg["sleepB"])
        keyboard.send_keys('{VK_F8}')  # 点击持仓选项卡
        self.__click_update_button()
        time.sleep(API_Config.cfg["sleepA"])
        df = self.__get_grid_data()
        self.__esc()
        return df

    def __trade(self):  # stock_no, amount
        """ 交易 """
        time.sleep(API_Config.cfg["sleepA"])
        # 设置最优五档即时成交剩余转撤销申报
        select = ""
        try:
            select = self.main_wnd.window(control_id=0x605, class_name="ComboBox")
        except:
            time.sleep(API_Config.cfg["sleepC"])
            select = self.main_wnd.window(control_id=0x605, class_name="ComboBox")

        time.sleep(API_Config.cfg["sleepA"])
        try:
            # 深A 索引4
            select.select(3)
        except:
            # 沪A 索引0
            select.select(0)

        time.sleep(API_Config.cfg["sleepA"])
        # 点击卖出or买入
        try:
            self.main_wnd.window(control_id=0x3EE, class_name="Button").click()
        except:
            time.sleep(API_Config.cfg["sleepC"])
            self.main_wnd.window(control_id=0x3EE, class_name="Button").click()

        # 系统设置 快速交易设置中 委托成功后弹出提示对话框  弹出对话框获取合同号
        time.sleep(API_Config.cfg["sleepB"])
        time.sleep(API_Config.cfg["sleepC"])  # 再等待1秒给交易预留
        self.__confirm_trade_dialog()

        result = self.__read_trade_result_text()
        if not result.strip():
            result = "委托已提交，但无法读取结果文本"

        return self.__parse_result(result)

    def __get_grid_data(self, is_records=False):
        """ 获取grid里面的数据 """
        time.sleep(API_Config.cfg["sleepC"])
        try:
            grid = self.main_wnd.window(control_id=0x417, class_name='CVirtualGridCtrl')
            grid.set_focus()
        except:
            time.sleep(API_Config.cfg["sleepC"])
            grid = self.main_wnd.window(control_id=0x417, class_name='CVirtualGridCtrl')
            grid.set_focus()

        last_error = None
        for _ in range(3):
            keyboard.send_keys('^a')
            time.sleep(API_Config.cfg["sleepA"])
            keyboard.send_keys('^c')
            time.sleep(API_Config.cfg["sleepB"])
            try:
                data = clipboard.GetData()
                if not data or not str(data).strip():
                    raise RuntimeError("clipboard is empty")
                df = pd.read_csv(io.StringIO(data), delimiter='\t', na_filter=False)
                if is_records:
                    return df.to_dict('records')
                return df
            except Exception as ex:
                last_error = ex
                print("读取表格剪贴板失败，准备重试:", ex)
                time.sleep(API_Config.cfg["sleepC"])

        print("读取表格剪贴板最终失败:", last_error)
        if is_records:
            return []
        return pd.DataFrame()

    def __select_menu(self, path):
        """ 点击左边菜单 """
        if r"网上股票" not in self.app.top_window().window_text():
            self.app.top_window().set_focus()
            pywinauto.keyboard.send_keys("{ENTER}")
        self.__get_left_menus_handle().get_item(path).click()

    def __get_left_menus_handle(self):
        while True:
            try:
                handle = ""
                try:
                    handle = self.main_wnd.window(control_id=0x81, class_name='SysTreeView32')
                except:
                    time.sleep(API_Config.cfg["sleepC"])
                    handle = self.main_wnd.window(control_id=0x81, class_name='SysTreeView32')
                handle.wait('ready', 2)
                return handle
            except Exception as ex:
                print(ex)
                pass

    def __click_update_button(self, allow_missing=False):
        """ 刷新按钮 """
        print('刷新')
        time.sleep(API_Config.cfg["sleepA"])
        try:
            self.main_wnd.window(control_id=0x8016, class_name='Button').click()
        except Exception as ex:
            if allow_missing:
                print("刷新按钮不可用，跳过刷新:", ex)
                return False
            time.sleep(API_Config.cfg["sleepC"])
            self.main_wnd.window(control_id=0x8016, class_name='Button').click()

        time.sleep(API_Config.cfg["sleepB"])
        return True

    @staticmethod
    def __parse_result(result):
        """ 解析买入卖出的结果 """
        # "您的买入委托已成功提交，合同编号：865912566。"
        # "您的卖出委托已成功提交，合同编号：865967836。"
        # "您的撤单委托已成功提交，合同编号：865967836。"
        # "系统正在清算中，请稍后重试！ "
        if r"已成功提交，合同编号：" in result:
            return {
                "success": True,
                "auto": True,  # True:自动化程序返回   False:接口程序返回
                "msg": result,
                "entrust_no": result.split("合同编号：")[1].split("。")[0]
            }
        else:
            return {
                "success": False,
                "auto": True,  # True:自动化程序返回   False:接口程序返回
                "msg": result
            }

    def __esc(self):
        time.sleep(API_Config.cfg["sleepB"])
        try:
            # self.app.top_window().window(control_id=0x3F0, class_name='Button').click()  # 二义性的弹窗右上角的关闭按钮
            self.app.top_window().set_focus()
            pywinauto.keyboard.send_keys('{VK_ESCAPE}')
            time.sleep(API_Config.cfg["sleepA"])
            try:
                self.app.top_window().window(control_id=0x3EF, class_name='Button').click()  # 重填按钮
            except:
                time.sleep(API_Config.cfg["sleepC"])
                self.app.top_window().window(control_id=0x3EF, class_name='Button').click()  # 重填按钮

        except:
            pass
        self.app.top_window().set_focus()
        pywinauto.keyboard.send_keys('{VK_ESCAPE}')
        time.sleep(API_Config.cfg["sleepA"])
        self.__select_menu([0])

    def __confirm_trade_dialog(self):
        """处理委托确认弹窗，自动按 y 确认"""
        try:
            for _ in range(8):
                top = self.app.top_window()
                title = top.window_text()
                try:
                    top.set_focus()
                except:
                    pass

                texts = []
                try:
                    texts = top.texts()
                except Exception as ex:
                    print("读取顶层文本失败:", ex)

                joined = " ".join([str(x) for x in texts])
                if ("委托确认" in title) or ("您是否确定以上市价买入委托" in joined) or ("您是否确定以上市价卖出委托" in joined) or ("买入数量" in joined and "证券代码" in joined) or ("撤单确认" in title) or ("撤销委托" in joined) or ("您是否确定撤销以上委托" in joined):
                    if self.__force_confirm_by_keys(top):
                        time.sleep(API_Config.cfg["sleepA"])
                        return
                    if self.__click_yes_button(top):
                        time.sleep(API_Config.cfg["sleepA"])
                        return
                elif title == '' and texts == ['']:
                    if self.__force_confirm_by_keys(top):
                        time.sleep(API_Config.cfg["sleepA"])
                        return
                time.sleep(API_Config.cfg["sleepA"])
        except Exception as ex:
            print("处理委托确认弹窗失败:", ex)

    def __force_confirm_by_keys(self, top):
        for keys in ['y', 'Y', '%Y', '{LEFT}{ENTER}', '{SPACE}', '{ENTER}']:
            try:
                print("尝试确认快捷键:", keys)
                top.set_focus()
                keyboard.send_keys(keys)
                time.sleep(API_Config.cfg["sleepA"])
                return True
            except Exception as ex:
                print("强制发送快捷键失败:", keys, ex)
        return False

    def __click_yes_button(self, top):
        try:
            top.set_focus()
        except:
            pass

        try:
            btn = top.child_window(title="是(Y)", control_type="Button")
            if btn.exists(timeout=1):
                btn.click_input()
                return True
        except Exception as ex:
            print("control_type按钮点击失败:", ex)

        try:
            btn = top.window(title="是(Y)", class_name='Button')
            if btn.exists():
                btn.click_input()
                return True
        except Exception as ex:
            print("class_name按钮点击失败:", ex)

        try:
            buttons = top.descendants(class_name='Button')
            for btn in buttons:
                try:
                    txts = btn.texts()
                    if txts and any(t in ['是(Y)', '是'] for t in txts):
                        btn.set_focus()
                        btn.click_input()
                        return True
                except Exception as ex:
                    print("遍历按钮失败:", ex)
        except Exception as ex:
            print("枚举按钮失败:", ex)

        try:
            buttons = top.descendants(class_name='Button')
            if buttons:
                left_btn = sorted(buttons, key=lambda b: (b.rectangle().top, b.rectangle().left))[0]
                left_btn.set_focus()
                left_btn.click_input()
                return True
        except Exception as ex:
            print("最靠前按钮点击失败:", ex)

        for keys in ['Y', '%Y', '{LEFT}{ENTER}', '{ENTER}']:
            try:
                top.set_focus()
                keyboard.send_keys(keys)
                time.sleep(API_Config.cfg["sleepA"])
                return True
            except Exception as ex:
                print("发送快捷键失败:", keys, ex)

        return False

    def __read_trade_result_text(self):
        try:
            top = self.app.top_window()
            result = top.window(control_id=0x3EC, class_name='Static')
            if result.exists():
                return result.window_text()
        except:
            pass

        time.sleep(API_Config.cfg["sleepC"])
        top = self.app.top_window()
        try:
            result = top.window(control_id=0x3EC, class_name='Static')
            if result.exists():
                text = result.window_text()
                return text
        except:
            pass

        try:
            texts = top.texts()
            for text in texts:
                if '合同编号' in str(text) or '已成功提交' in str(text) or '系统正在清算中' in str(text):
                    return str(text)
        except:
            pass
        return ''

    def __close_result_dialog(self):
        try:
            top = self.app.top_window()
            top.set_focus()
            top.window(control_id=0x2, class_name='Button').click()
            return
        except:
            pass

        try:
            top = self.app.top_window()
            top.set_focus()
            time.sleep(API_Config.cfg["sleepC"])
            top.window(control_id=0x2, class_name='Button').click()
            return
        except:
            pass

        try:
            for btn in self.app.top_window().children(class_name='Button'):
                txts = btn.texts()
                if txts and ('确定' in txts[0] or '确认' in txts[0] or txts[0] == '是(Y)'):
                    btn.click()
                    return
        except:
            pass

    def __activate_cancel_target(self, row_index):
        try:
            grid = self.main_wnd.window(control_id=0x417, class_name='CVirtualGridCtrl')
            grid.set_focus()
        except Exception as ex:
            print("撤单grid聚焦失败:", ex)
            return False

        try:
            keyboard.send_keys('{HOME}')
            time.sleep(API_Config.cfg["sleepA"])
            for _ in range(int(row_index)):
                keyboard.send_keys('{DOWN}')
                time.sleep(API_Config.cfg["sleepA"])
            print("已定位目标行，尝试勾选")
            keyboard.send_keys('{SPACE}')
            time.sleep(API_Config.cfg["sleepB"])
            return True
        except Exception as ex:
            print("撤单行选中失败:", ex)
            return False

    def __trigger_cancel_action(self):
        try:
            self.app.top_window().set_focus()
        except Exception:
            pass

        candidates = ['撤买(X)', '撤买1(X)', '撤单(Del)', '撤买', '撤单', '撤销']
        try:
            buttons = self.main_wnd.children(class_name='Button')
            for target in candidates:
                for btn in buttons:
                    try:
                        txts = btn.texts()
                        if txts and txts[0].strip() == target:
                            print("命中撤买按钮:", txts)
                            btn.click()
                            time.sleep(API_Config.cfg["sleepB"])
                            return True
                    except Exception:
                        continue
        except Exception as ex:
            print("枚举主窗口按钮失败:", ex)

        for keys in ['X', 'x', '%x']:
            try:
                print("尝试撤单热键:", keys)
                self.app.top_window().set_focus()
                keyboard.send_keys(keys)
                time.sleep(API_Config.cfg["sleepB"])
                return True
            except Exception as ex:
                print("撤单热键失败:", keys, ex)

        return False

    def __normalize_entrust_df(self, df):
        try:
            normalized = df.copy()
        except Exception:
            return None

        normalized.columns = [str(col).strip() for col in normalized.columns]
        if '合同编号' not in normalized.columns:
            for candidate in ['合同编号 ', '合同编号\t', '合同号']:
                if candidate in normalized.columns:
                    normalized = normalized.rename(columns={candidate: '合同编号'})
                    break

        if '合同编号' in normalized.columns:
            normalized['合同编号'] = normalized['合同编号'].astype(str).str.strip()

        return normalized