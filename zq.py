import sqlite3
import aiohttp
import variable
import config
from collections import defaultdict
import asyncio
import re
import os
import time
from typing import Any
import asyncio


# 假设 delete_later, config, variable, query_records 等已经在外部定义
# 如果没有定义，请确保引入它们

async def zq_user(client, event):
    # 1. 使用 split() 不带参数，可以自动处理多个连续空格
    args = event.raw_text.strip().split()
    if not args:
        return

    cmd = args[0].lower()  # 统一转小写，防止大小写敏感问题

    # --- 辅助函数：统一发送回执并添加定时删除任务 ---
    async def reply_temp(text, delay=10, parse_mode="markdown"):
        try:
            msg = await client.send_message(config.group, text, parse_mode=parse_mode)
            # 创建删除任务 (用户消息 + 机器人回复)
            asyncio.create_task(delete_later(client, event.chat_id, event.id, delay))
            asyncio.create_task(delete_later(client, msg.chat_id, msg.id, delay))
        except Exception as e:
            print(f"发送消息失败: {e}")

    # --- 具体的命令处理逻辑 ---

    async def cmd_help():
        help_message = """```使用方法：
- st - 启动命令 (st ys_name )
- res - 重置统计数据 (res)
- set - 设置参数：炸几次触发 赢利多少触发 炸停止多久 盈利停止多久 重置恢复局数 [可选:立即恢复(1)] (set 1 1000000 1 1 2)
- ms - 切换模式：模式(0反投,1追投,2占比) 赢翻倍局数 [可选:占比追投参数] (ms 2 0 3 1000)
- cl - 删除群组消息 (cl)
- top - 显示捐赠排行榜 (top)
- ys - 保存预设策略 (ys yc 30 3 3.0 3.0 3.0 3.0 10000)
- yss - 查看或删除预设 (yss 或 yss dl yc)
- js - 计算预设所需资金 (js ys1)
- h - 查看帮助```"""
        await reply_temp(help_message, delay=60)

    async def cmd_start():
        yss = query_records(args[1])
        if not yss:
            await reply_temp("❌ 策略不存在")
            return

        variable.continuous = yss["count"]
        variable.lose_stop = yss["field2"]
        variable.lose_once = yss["field3"]
        variable.lose_twice = yss["field4"]
        variable.lose_three = yss["field5"]
        variable.lose_four = yss["field6"]
        variable.initial_amount = yss["amount"]
        await reply_temp(f"""启动 {yss["type"]}""")

    async def cmd_reset():
        variable.win_total = 0
        variable.total = 0
        variable.earnings = 0
        await reply_temp("重置成功")

    async def cmd_set():
        variable.explode = int(args[1])
        variable.profit = int(args[2])
        variable.stop = int(args[3])
        variable.profit_stop = int(args[4])
        if len(args) > 5:
            variable.stop_count = int(args[5])
        await reply_temp("设置成功")

    async def cmd_mode():
        variable.mode = int(args[1])
        variable.win = int(args[2])
        if int(args[1]) == 2:
            variable.chase = int(args[3])
            variable.proportion = int(args[4])
        await reply_temp("设置成功")

    async def cmd_clean():
        target_groups = [-1002262543959, -1001833464786]
        for g in target_groups:
            # 使用列表推导式优化，或直接传递迭代器(视Telethon版本而定)
            # 注意：iter_messages 是异步生成器
            messages = [msg.id async for msg in client.iter_messages(g, from_user='me')]
            if messages:
                await client.delete_messages(g, messages)
        # 这里只删除触发命令的那条消息，时间短一点
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 3))

    async def cmd_balance():
        variable.balance = int(args[1])
        await reply_temp("余额设置成功")

    async def cmd_top():
        users = count_users()
        if users <= 0:
            await reply_temp("**暂无记录**")
            return

        all_users = query_users(config.zq_bot, order="DESC")
        donation_list = [f"```当前{config.name}个人总榜Top: {len(all_users)} 为"]

        # 优化字符串拼接
        for i, item in enumerate(all_users[:20], start=1):
            donation_list.append(
                f"     总榜Top {i}: {item['name']} 大佬共赏赐小弟: {item['count']} 次,共计: {format_number(int(item['amount']))} 爱心\n"
                f"{config.name} 共赏赐 {item['name']} 小弟： {item['neg_count']} 次,共计： {format_number(int(item['neg_amount']))} 爱心"
            )
        donation_list.append("```")
        await reply_temp("\n".join(donation_list), delay=60)

    async def cmd_ys():
        # 参数转换比较多，直接传参
        name = args[1]
        params = [int(args[2]), int(args[3]), float(args[4]), float(args[5]), float(args[6]), float(args[7]),
                  int(args[8])]

        ys = query_records(name)
        if ys is not None:
            mes = update_record(name, *params)  # 使用解包传递参数
        else:
            mes = add_record(name, *params)
        await reply_temp(mes)

    async def cmd_yss():
        if len(args) > 2 and args[1] == "dl":
            mes = delete_record(args[2])
            await reply_temp(mes)
            return

        if count_records() > 0:
            yss_data = query_records()
            mes = "```\n" + "\n\n".join(
                f"{ys['type']}: {ys['count']}局反投 押注{ys['field2']}次 金额 {ys['amount']}\n"
                f"倍率 {ys['field3']} / {ys['field4']} / {ys['field5']} / {ys['field6']}"
                for ys in yss_data
            ) + "\n```"
            await reply_temp(mes, delay=60)
        else:
            await reply_temp("**暂无预设记录**")

    async def cmd_js():
        ys = query_records(args[1])
        if ys is not None:
            js_val = calculate_losses(ys["field2"], ys["amount"], ys["field3"], ys["field4"], ys["field5"],
                                      ys["field6"])
            mes = f"累计需要资金：{int(js_val)}"
        else:
            mes = "策略不存在"
        await reply_temp(mes)

    # --- 命令路由表 ---
    handlers = {
        "h": cmd_help,
        "help": cmd_help,
        "st": cmd_start,
        "res": cmd_reset,
        "set": cmd_set,
        "ms": cmd_mode,
        "cl": cmd_clean,
        "ye": cmd_balance,
        "top": cmd_top,
        "ys": cmd_ys,
        "yss": cmd_yss,
        "js": cmd_js
    }

    # --- 执行逻辑 ---
    if cmd in handlers:
        try:
            await handlers[cmd]()
        except (IndexError, ValueError) as e:
            # 捕获参数缺失(IndexError)或类型错误(ValueError)
            await reply_temp(f"❌ 命令执行错误: 参数缺失或格式不对。\nError: {str(e)}")
        except Exception as e:
            # 捕获其他未知错误
            await reply_temp(f"❌ 系统错误: {str(e)}")


class MessageDeduplicator:
    def __init__(self, time_window: float = 50.0):
        """
        初始化消息去重器
        :param time_window: 时间窗口（秒），默认为5秒
        """
        self.last_message = None
        self.last_timestamp = 0.0
        self.time_window = time_window

    def should_process(self, message: Any) -> bool:
        """
        判断是否应该处理该消息
        :param message: 接收到的消息
        :return: True 表示需要处理，False 表示重复消息
        """
        current_time = time.time()

        # 如果是第一条消息，直接处理
        if self.last_message is None:
            self.last_message = message
            self.last_timestamp = current_time
            return True

        # 检查是否在时间窗口内
        is_duplicate = (current_time - self.last_timestamp) < self.time_window

        # 更新最后的消息信息
        self.last_message = message
        self.last_timestamp = current_time

        # 如果在时间窗口内，认为是重复消息，不处理
        return not is_duplicate

    def reset(self):
        """重置去重器状态"""
        self.last_message = None
        self.last_timestamp = 0.0


async def zq_bet_on(client, event, deduplicator):
    if deduplicator.should_process(event):
        await asyncio.sleep(5)
        if variable.balance > 0 and (variable.balance - calculate_bet_amount(variable.win_count, variable.lose_count,
                                                                             variable.initial_amount,
                                                                             variable.lose_stop, variable.lose_once,
                                                                             variable.lose_twice,
                                                                             variable.lose_three,
                                                                             variable.lose_four, 0)) >= 0:
            if variable.bet_on or (variable.mode == 1 and variable.mode_stop) or (
                    variable.mode == 2 and variable.mode_stop):
                # 判断是否是开盘信息
                if event.reply_markup:
                    print(f"开始押注！")
                    # 获取压大还是小
                    if variable.mode == 1:
                        check = z_next_trend(variable.history)
                    elif variable.mode == 0:
                        check = predict_next_trend(variable.history)
                    else:
                        check = next_trend(variable.history)
                    print(f"本次押注：{check}")
                    # 获取押注金额 根据连胜局数和底价进行计算
                    variable.bet_amount = calculate_bet_amount(variable.win_count, variable.lose_count,
                                                               variable.initial_amount,
                                                               variable.lose_stop, variable.lose_once,
                                                               variable.lose_twice,
                                                               variable.lose_three, variable.lose_four, 1)
                    # 获取要点击的按钮集合
                    com = find_combination(variable.bet_amount)
                    print(f"本次押注金额：{com}")
                    # 押注
                    if len(com) > 0:
                        variable.bet = True
                        await bet(check, com, event)
                        mes = f"""
                        **⚡ 押注： {"押大" if check else "押小"}
    💵 金额： {variable.bet_amount}**
                        """
                        m = await client.send_message(config.group, mes, parse_mode="markdown")
                        asyncio.create_task(delete_later(client, m.chat_id, m.id, 60))
                        variable.mark = True
                    else:
                        # if variable.mode != 0:
                        if variable.mark:
                            variable.explode_count += 1
                            print("触发停止押注")
                            variable.mark = False
                        variable.bet = False
                        if variable.mode == 1 or variable.mode == 2:
                            variable.win_count = 0
                            variable.lose_count = 0
            else:
                variable.bet = False
        else:
            variable.bet = False
            variable.win_count = 0
            variable.lose_count = 0
            m = await client.send_message(config.group, f"**没有足够资金进行押注 请重置余额**")
            asyncio.create_task(delete_later(client, m.chat_id, m.id, 60))
    else:
        print(f"忽略重复消息（时间窗口内）: {event.id}")


# 3.3 异步获取账户余额
async def fetch_account_balance():
    """异步获取账户余额，失败时返回旧值"""
    headers = {
        "Cookie": config.ZHUQUE_COOKIE,
        "X-Csrf-Token": config.ZHUQUE_X_CSRF
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(config.ZHUQUE_API_URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=5)) as response:
                data = await response.json()
                return int(data.get("data", {}).get("bonus", variable.balance))
    except Exception:
        return variable.balance


def calculate_losses(cycles, initial, rate1, rate2, rate3, rate4):
    total = 0
    current_bet = initial
    for i in range(cycles):
        # 累加当前押注金额
        total += current_bet

        # 确定当前阶段倍数
        if i < 3:
            rate = [rate1, rate2, rate3][i]
        else:
            rate = rate4

        # 计算基础押注金额
        base_bet = current_bet * rate

        # 计算并处理额外金额（下次金额的1%取500整倍数）
        additional = closest_multiple_of_500((base_bet * 0.01))

        # 更新押注金额（基础金额 + 处理后的额外金额）
        current_bet = base_bet + additional

    return total


def z_next_trend(history):
    """
    追投
    """
    return history[-1]


def next_trend(history):
    """
    占比追投
    """
    # 获取列表的最后 n 个元素
    last_n_elements = history[-variable.chase:]
    # 判断这些元素是否都相同
    # 将切片转换为集合，如果所有元素相同，集合的长度就是1
    if len(set(last_n_elements)) == 1:
        # 如果相同，返回列表的最后一个元素
        return history[-1]
    # 不相同按照占比押注
    # 获取列表总长度
    total_count = len(history[-variable.proportion:])
    # 统计 1 的数量
    ones_count = history[-variable.proportion:].count(1)
    # 计算 1 的占比
    ratio_of_ones = ones_count / total_count
    # 判断占比并返回结果
    if ratio_of_ones > 0.5:
        return 0
    else:
        return 1


def predict_next_trend(history):
    return 0 if history[-1] else 1


def calculate_bet_amount(win_count, lose_count, initial_amount, lose_stop, lose_once, lose_twice, lose_three,
                         lose_four, i):
    if win_count == 0 and lose_count == 0:
        return closest_multiple_of_500(initial_amount)
    elif win_count > 0 and lose_count == 0:
        if win_count == 1:
            return closest_multiple_of_500(initial_amount)
        if 0 < (win_count - 1) < variable.win:
            return closest_multiple_of_500(variable.bet_amount * 2)
        if (win_count - 1) >= variable.win:
            return variable.bet_amount
    else:
        if (lose_count + 1) > lose_stop:
            return 0
        if lose_count == 1:
            return closest_multiple_of_500(initial_amount * lose_once)
        if lose_count == 2:
            return closest_multiple_of_500(variable.bet_amount * lose_twice)
        if lose_count == 3:
            return closest_multiple_of_500(variable.bet_amount * lose_three)
        return closest_multiple_of_500(variable.bet_amount * lose_four)


def find_combination(target):
    """
    处理押注金额  生成要点击按钮集合
    """
    # 数字集合
    numbers = [500, 2000, 20000, 50000, 250000, 1000000, 5000000, 50000000]
    # 将数字从大到小排序
    numbers.sort(reverse=True)
    combination = []

    for num in numbers:
        while target >= num:
            combination.append(num)
            target -= num

    if target == 0:
        return combination
    else:
        return None  # 如果无法拼凑，返回 None


def closest_multiple_of_500(n):
    """
    返回最接近给定数值的500的倍数。

    :param n: 输入的数值
    :return: 最接近的500的倍数
    """
    # 四舍五入到最近的500倍数
    return round(n / 500) * 500


async def bet(check, com, event):
    variable.total += 1
    if check:
        for c in com:
            await event.click(variable.big_button[c])  # 点击按钮
            await asyncio.sleep(1.5)
        variable.bet_type = 1
    else:
        for c in com:
            await event.click(variable.small_button[c])  # 点击按钮
            await asyncio.sleep(1.5)
        variable.bet_type = 0


async def zq_settle(client, event):
    if event.pattern_match:
        # 存储历史记录
        if len(variable.history) >= 1000:
            del variable.history[:5]
        if event.pattern_match.group(2) == variable.consequence:
            variable.win_times += 1
            variable.lose_times = 0
            variable.history.append(1 if event.pattern_match.group(2) == variable.consequence else 0)
            variable.a_history.append(1 if event.pattern_match.group(2) == variable.consequence else 0)
        else:
            variable.win_times = 0
            variable.lose_times += 1
            variable.history.append(1 if event.pattern_match.group(2) == variable.consequence else 0)
            variable.a_history.append(1 if event.pattern_match.group(2) == variable.consequence else 0)

        if len(variable.a_history) >= 1000:
            mes = f"""
📊 **近期 1000 次连输连赢次数\n{os.linesep.join(
                " ".join(map(str, variable.a_history[i:i + 20]))
                for i in range(0, len(variable.a_history), 20)
            )}"""
            await client.send_message(config.group, mes, parse_mode="markdown")
            variable.a_history.clear()
        # 存储输赢历史记录
        if len(variable.lose_history) >= 1000:
            del variable.lose_history[:5]

        # 统计连大连小次数
        whether_bet_on(variable.win_times, variable.lose_times)

        if variable.bet:
            if event.pattern_match.group(2) == variable.consequence:
                if variable.bet_type == 1:
                    variable.win_total += 1
                    variable.earnings += (int(variable.bet_amount * 0.99))
                    variable.period_profit += (int(variable.bet_amount * 0.99))
                    variable.balance += (int(variable.bet_amount * 0.99))
                    variable.win_count += 1
                    variable.lose_count = 0
                    variable.status = 1
                    variable.lose_history.append(1)
                else:
                    variable.earnings -= variable.bet_amount
                    variable.period_profit -= variable.bet_amount
                    variable.balance -= variable.bet_amount
                    variable.win_count = 0
                    variable.lose_count += 1
                    variable.status = 0
                    variable.lose_history.append(0)
            else:
                if variable.bet_type == 0:
                    variable.win_total += 1
                    variable.earnings += (int(variable.bet_amount * 0.99))
                    variable.period_profit += (int(variable.bet_amount * 0.99))
                    variable.balance += (int(variable.bet_amount * 0.99))
                    variable.win_count += 1
                    variable.lose_count = 0
                    variable.status = 1
                    variable.lose_history.append(1)
                else:
                    variable.earnings -= variable.bet_amount
                    variable.period_profit -= variable.bet_amount
                    variable.balance -= variable.bet_amount
                    variable.win_count = 0
                    variable.lose_count += 1
                    variable.status = 0
                    variable.lose_history.append(0)

        else:
            variable.lose_history.append(3)

        if variable.explode_count >= variable.explode or variable.period_profit >= variable.profit:
            if variable.flag:
                variable.flag = False
                if variable.explode_count >= variable.explode:
                    mes = f"""**💥 本轮炸了收益如下：{variable.period_profit} 灵石**\n"""
                    await client.send_message(config.group, mes, parse_mode="markdown")
                    variable.stop_count = variable.stop
                elif variable.period_profit >= variable.profit:
                    mes = f"""**📈 本轮赢了一共赢得：{variable.period_profit} 灵石**"""
                    await client.send_message(config.group, mes, parse_mode="markdown")
                    variable.stop_count = variable.profit_stop
                else:
                    variable.stop_count = variable.stop
            if variable.stop_count > 0:
                variable.stop_count -= 1
                variable.bet_on = False
                variable.mode_stop = False
            else:
                variable.explode_count = 0
                variable.period_profit = 0
                variable.mode_stop = True
                variable.flag = True
                variable.win_count = 0
                variable.lose_count = 0
                mes = f"""恢复押注"""
                message = await client.send_message(config.group, mes, parse_mode="markdown")
                asyncio.create_task(delete_later(client, message.chat_id, message.id, 30))

        # 获取统计结果
        if len(variable.history) > 3:
            if len(variable.history) % 10 == 0:
                variable.balance = await fetch_account_balance()
                if variable.message1 is not None:
                    await variable.message1.delete()
                if variable.message3 is not None:
                    await variable.message3.delete()
                if variable.message4 is not None:
                    await variable.message4.delete()
                result_counts = count_consecutive(variable.history)
                # 创建消息
                mes = f"""
                📊 **最近 1000 局：**
🔴 **连“小”结果：**
{format_counts(result_counts["小"], "小")}
🟢 **连“大”结果：**
{format_counts(result_counts["大"], "大")}
                """
                variable.message1 = await client.send_message(config.group, mes, parse_mode="markdown")
                result_counts = count_consecutive(variable.history[-200::])
                # 创建消息
                mes = f"""
                📊 **最近 200 局：**
🔴 **连“小”结果：**
{format_counts(result_counts["小"], "小")}
🟢 **连“大”结果：**
{format_counts(result_counts["大"], "大")}
                 """
                variable.message3 = await client.send_message(config.group, mes, parse_mode="markdown")
                result_mes = count_sequences(variable.lose_history)
                variable.message4 = await client.send_message(config.group, result_mes, parse_mode="markdown")
        if variable.message is not None:
            await variable.message.delete()
        reversed_data = ["✅" if x == 1 else "❌" for x in variable.history[-40::][::-1]]  # 倒序列表
        # reversed_data = variable.history[-200::][::-1]  # 倒序列表
        mes = f"""
        📊 **近期 40 次结果**（由近及远）\n✅：大（1）  ❌：小（0）\n{os.linesep.join(
            " ".join(map(str, reversed_data[i:i + 10]))
            for i in range(0, len(reversed_data), 10)
        )}\n\n———————————————\n🎯 **策略设定**\n"""
        if variable.mode == 0:
            mes += f"""🎰 **押注模式 反投**\n🔄 **{variable.continuous} 连反压**\n"""
        elif variable.mode == 1:
            mes += f"""🎰 **押注模式 预测**\n"""
        else:
            mes += f"""🎰 **押注模式 追投**\n"""
        mes += f"""💰 **初始金额：{variable.initial_amount}**\n"""
        mes += f"""⏹ **押注 {variable.lose_stop} 次停止**\n"""
        mes += f"""💥 **炸 {variable.explode} 次 暂停 {variable.stop} 局**\n"""
        mes += f"""📈 **盈利 {variable.profit} 暂停 {variable.profit_stop} 局 **\n"""
        mes += f"""📈 **本轮盈利 {variable.period_profit}\n📉 押注倍率 {variable.lose_once} / {variable.lose_twice} / {variable.lose_three} / {variable.lose_four} **\n"""
        mes += f"""📈 **赢翻倍局数 {variable.win}**\n"""
        if variable.win_total > 0:
            mes += f"""🎯 **押注次数：{variable.total}\n🏆 胜率：{variable.win_total / variable.total * 100:.2f}%**\n"""
        mes += f"""💰 **收益：{variable.earnings}\n💰 总余额：{variable.balance}**\n"""
        if variable.stop_count >= 1:
            mes += f"""\n\n还剩 {variable.stop_count} 局恢复押注"""
        if variable.bet:
            mess = f"""**📉 输赢统计： {"赢" if variable.status else "输"} {int((variable.bet_amount * 0.99)) if variable.status else (variable.bet_amount)}\n🎲 结果： {event.pattern_match.group(2)}**"""
            m = await client.send_message(config.group, mess, parse_mode="markdown")
            asyncio.create_task(delete_later(client, m.chat_id, m.id, 60))
        variable.message = await client.send_message(config.group, mes, parse_mode="markdown")
        # 根据是否押注来统计 胜率和押注局数


async def qz_red_packet(client, event, functions):
    if event.reply_markup:
        print("消息包含按钮！")

        # 遍历按钮
        for row in event.reply_markup.rows:
            for button in row.buttons:
                if hasattr(button, 'data'):  # 内联按钮
                    print(f"发现内联按钮：{button.text}, 数据：{button.data}")
                else:  # 普通按钮
                    print(f"发现普通按钮：{button.text}")
                    # 点击第一个按钮（假设是内联按钮）
                i = 0
                while i < 30:
                    if event.reply_markup.rows[0].buttons[0].data:
                        await event.click(0)  # 点击第一个按钮
                        response = await client(functions.messages.GetBotCallbackAnswerRequest(
                            peer=event.chat_id,  # 目标聊天
                            msg_id=event.id,  # 消息 ID
                            data=button.data  # 按钮的 callback_data
                        ))
                        if response.message:
                            if re.search(r"已获得 (\d+) 灵石", response.message):
                                # 匹配 "已获得 xxx 灵石"
                                bonus = re.search(r"已获得 (\d+) 灵石", response.message).group(1)
                                await client.send_message(config.group, f"🎉 抢到红包{bonus}灵石！")
                                print("你成功领取了灵石！")
                                return
                            elif re.search("不能重复领取", response.message):
                                # 匹配 "不能重复领取"
                                await client.send_message(config.group, f"⚠️ 抢到红包，但是没有获取到灵石数量！")
                                print("不能重复领取的提示")
                                return
                        await asyncio.sleep(1)
                        i += 1


def whether_bet_on(win_times, lose_times):
    if win_times >= variable.continuous or lose_times >= variable.continuous and len(
            variable.history) >= variable.continuous:
        variable.bet_on = True
    else:
        variable.bet_on = False
        if variable.mode == 0:
            variable.win_count = 0
            variable.lose_count = 0


def count_sequences(records):
    # 初始化统计字典
    loss_counts = {}
    win_counts = {}

    # 边界处理：空记录
    if not records:
        print("**🔴 连“输”结果：\n🟢 连“赢”结果：**")
        return

    # 初始化计数变量
    current = records[0]
    count = 1

    # 遍历记录序列
    for i in range(1, len(records)):
        if records[i] == current:
            count += 1
        else:
            # 根据当前状态更新对应字典
            if current == 0:
                loss_counts[count] = loss_counts.get(count, 0) + 1
            elif current == 1:
                win_counts[count] = win_counts.get(count, 0) + 1
            current = records[i]
            count = 1

    # 处理最后一组连续记录
    if current == 0:
        loss_counts[count] = loss_counts.get(count, 0) + 1
    elif current == 1:
        win_counts[count] = win_counts.get(count, 0) + 1

    # 按连续次数降序排序
    sorted_loss = sorted(loss_counts.items(), key=lambda x: x[0], reverse=True)
    sorted_win = sorted(win_counts.items(), key=lambda x: x[0], reverse=True)

    # 格式化输出结果
    output = "🔴 **连“输”结果：**\n"
    for length, times in sorted_loss:
        output += f"{length} 连“输” : {times} 次\n"

    output += "🟢 **连“赢”结果：**\n"
    for length, times in sorted_win:
        output += f"{length} 连“赢” : {times} 次\n"

    return output.rstrip()


def count_consecutive(data):
    """统计连续出现的次数"""
    counts = {"大": defaultdict(int), "小": defaultdict(int)}
    current_value = data[0]  # 记录当前数字（1 或 0）
    current_count = 1  # 当前连胜的次数

    for i in range(1, len(data)):
        if data[i] == current_value:
            current_count += 1
        else:
            # 记录当前连胜的次数
            label = "大" if current_value == 1 else "小"
            counts[label][current_count] += 1
            # 更新计数
            current_value = data[i]
            current_count = 1

    # 处理最后一组连续数字
    label = "大" if current_value == 1 else "小"
    counts[label][current_count] += 1

    return counts


# 格式化输出
def format_counts(counts, label):
    return os.linesep.join([f"{key} 连“{label}” : {counts[key]} 次" for key in sorted(counts.keys(), reverse=True)])


async def zq_shoot(client, event):
    # 获取当前消息的回复消息
    current_message_id = event.reply_to_msg_id
    if current_message_id:
        # 获取上一条消息（即当前消息的回复消息）
        message1 = await client.get_messages(event.chat_id, ids=current_message_id)
        # 是自己转账给别人
        if message1.sender_id == config.user:
            if message1.reply_to_msg_id:
                # 获取被转帐人信息
                message2 = await client.get_messages(event.chat_id, ids=message1.reply_to_msg_id)
                user_id = message2.sender.id
                user_name = message2.sender.first_name
                match = re.search(r"\+(\d+)", message1.raw_text)
                amount = 0
                if match:
                    amount = match.group(1)
                # 查询用户数据
                user = query_users(event.sender_id, user_id)
                if user is not None:
                    update_user(event.sender_id, user_id, name=user_name, neg_amount=user["neg_amount"] + int(amount),
                                neg_count=user["neg_count"] + 1)
                else:
                    add_user(event.sender_id, user_id, name=user_name, amount=0, count=0, neg_amount=int(amount),
                             neg_count=1)

                user = query_users(event.sender_id, user_id)
                donation_list = f"大哥赏了你 {user["neg_count"]} 次 一共 {format_number(user["neg_amount"])} 爱心！\n 这可是我的血汗钱，别乱花哦"
                ms = await client.send_message(event.chat_id, donation_list, reply_to=message2.id)
                await asyncio.sleep(30)
                await ms.delete()
        # 获取上一条消息的回复（即上一条消息的上一条）
        if message1.reply_to_msg_id:
            message2 = await client.get_messages(event.chat_id, ids=message1.reply_to_msg_id)
            if message2.from_id.user_id == config.user:
                # 获取大佬的id
                user_id = message1.sender.id
                user_name = message1.sender.first_name
                match = re.search(r"\+(\d+)", message1.raw_text)
                amount = 0
                if match:
                    amount = match.group(1)
                print(f"收到来自他人的转账人id:{user_id}  名称：{user_name}   金额：{amount}")
                # 查询用户数据
                user = query_users(event.sender_id, user_id)
                if user is not None:
                    update_user(event.sender_id, user_id, name=user_name, amount=user["amount"] + int(amount),
                                count=user["count"] + 1)
                    await client.send_message(config.group, f"{user_name} 向您转账 {amount} 爱心",
                                              parse_mode="markdown")
                else:
                    add_user(event.sender_id, user_id, name=user_name, amount=int(amount), count=1, neg_amount=0,
                             neg_count=0)
                    await client.send_message(config.group, f"{user_name} 向您转账 {amount} 爱心",
                                              parse_mode="markdown")

                all_users = query_users(event.sender_id, order="DESC")
                # 找到当前用户在排序中的位置
                user = query_users(event.sender_id, user_id)
                index = next((i for i, item in enumerate(all_users) if item["user_id"] == user["user_id"]), -1)
                # 生成捐赠榜文本
                donation_list = f"```感谢 {user_name} 大佬赏赐的: {format_number(int(amount))} 爱心\n"
                donation_list += f"大佬您共赏赐了小弟: {user["count"]} 次,共计: {format_number(user["amount"])} 爱心\n"
                # donation_list += f"您是{config.name}个人打赏总榜的Top: {index + 1}\n\n"
                # donation_list += f"当前{config.name}个人总榜Top: 5 为\n"
                # # 添加总榜 Top 5
                # for i, item in enumerate(all_users[:5], start=1):
                #     name = item['name']
                #     count = item['count']
                #     am = item['amount']
                #     donation_list += f"     总榜Top {i}: {mask_if_less(int(amount), config.top, name)} 大佬共赏赐小弟: {mask_if_less(int(amount), config.top, count)} 次,共计: {mask_if_less(int(amount), config.top, format_number(int(am)))} 爱心\n"
                # donation_list += f"\n单次打赏>={format_number(config.top)}魔力查看打赏榜，感谢大佬，并期待您的下次打赏\n"
                # donation_list += f"小弟给大佬您共孝敬了: {user["neg_count"]} 次,共计: {format_number(user["neg_amount"])} 爱心"
                # donation_list += f"\n二狗哥出品，必属精品```"
                donation_list += f"```"
                ms = await client.send_message(event.chat_id, donation_list, reply_to=message1.id)
                await asyncio.sleep(30)
                await ms.delete()


def format_number(number: int) -> str:
    return f"{number:,}"


def mask_if_less(num1: int, num2: int, s) -> str:
    """
    如果 num1 小于 num2，则将 s 替换为等长的 '*'，否则返回 s 原值
    :param num1: 第一个整数，必须小于 num2
    :param num2: 第二个整数，必须大于 num1
    :param s: 需要处理的任意类型数据
    :return: 处理后的字符串
    """
    # 将第三个参数转换为字符串，支持多种数据类型
    s = str(s)

    # 判断条件，如果 num1 小于 num2，返回等长的 '*'
    return '*' * len(s) if num1 < num2 else s


async def delete_later(client, chat_id, msg_id, delay):
    """在后台等待 `delay` 秒后删除消息"""
    await asyncio.sleep(delay)
    await client.delete_messages(chat_id, msg_id)


# 数据库文件名
USERS_FILE = 'users.db'
YS_DATA_FILE = 'ys_data.db'


# 检查表是否存在并创建表
def create_table_if_not_exists():
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone() is None:
            # 表不存在，创建表
            cursor.execute('''
                CREATE TABLE users (
                    bot_id INTEGER,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    amount REAL DEFAULT 0.0,
                    count INTEGER DEFAULT 0,
                    neg_amount REAL DEFAULT 0.0,
                    neg_count INTEGER DEFAULT 0,
                    PRIMARY KEY (bot_id, user_id)
                )
            ''')
            print("表 'users' 已创建")
        else:
            print("表 'users' 已存在，无需创建")
        # 检查表是否存在，不存在则创建
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ys_data'")
        if cursor.fetchone() is None:
            cursor.execute('''
                CREATE TABLE ys_data (
                    type TEXT PRIMARY KEY,
                    count INTEGER,
                    field2 INTEGER,
                    field3 REAL,
                    field4 REAL,
                    field5 REAL,
                    field6 REAL,
                    amount INTEGER
                )
            ''')
            print("表 'ys_data' 已创建")
        else:
            print("表 'ys_data' 已存在，无需创建")


data = {
    "5697370563": [
        {"id": 9999, "name": "川普", "amount": 100, "count": 1, "-amount": 200, "-count": 1},
    ]
}


# 初始化数据   如需要写入历史数据使用此方法
def init_database():
    create_table_if_not_exists()  # 先检查并创建表
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        # 插入所有数据
        users_data = [(int(bot_id), item['id'], item['name'], float(item['amount']), item['count'],
                       float(item['-amount']), item['-count'])
                      for bot_id, items in data.items() for item in items]
        cursor.executemany('''
            INSERT OR REPLACE INTO users (bot_id, user_id, name, amount, count, neg_amount, neg_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', users_data)
        conn.commit()
    print("数据初始化完成，数据条数:", len(users_data))


# 添加新记录
def add_user(bot_id, user_id, name, amount=0.0, count=0, neg_amount=0.0, neg_count=0):
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (bot_id, user_id, name, amount, count, neg_amount, neg_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (bot_id, user_id, name, float(amount), count, float(neg_amount), neg_count))
        conn.commit()
    print(f"已添加用户: {name} (Bot ID: {bot_id}, User ID: {user_id})")


# 更新用户数据
def update_user(bot_id, user_id, name=None, amount=None, count=None, neg_amount=None, neg_count=None):
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if amount is not None:
            updates.append("amount = ?")
            params.append(float(amount))
        if count is not None:
            updates.append("count = ?")
            params.append(count)
        if neg_amount is not None:
            updates.append("neg_amount = ?")
            params.append(float(neg_amount))
        if neg_count is not None:
            updates.append("neg_count = ?")
            params.append(neg_count)

        if updates:
            params.extend([bot_id, user_id])
            query = f"UPDATE users SET {', '.join(updates)} WHERE bot_id = ? AND user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            if cursor.rowcount > 0:
                print(f"已更新用户 (Bot ID: {bot_id}, User ID: {user_id})")
            else:
                print(f"未找到用户 (Bot ID: {bot_id}, User ID: {user_id})")
        else:
            print("没有提供更新数据")


# 查询所有用户或根据 bot_id 和 user_id 查询
def query_users(bot_id=None, user_id=None, order=None):
    with sqlite3.connect(USERS_FILE) as conn:
        conn.row_factory = sqlite3.Row  # 返回字典格式
        cursor = conn.cursor()
        base_query = "SELECT bot_id, user_id, name, amount, count, neg_amount, neg_count FROM users"
        order_clause = ""

        # 处理排序
        if order == "ASC":
            order_clause = " ORDER BY amount ASC"
        elif order == "DESC":
            order_clause = " ORDER BY amount DESC"

        if bot_id is None and user_id is None:
            cursor.execute(base_query + order_clause)
            return [dict(row) for row in cursor.fetchall()]
        elif bot_id is not None and user_id is not None:
            cursor.execute(base_query + " WHERE bot_id = ? AND user_id = ?", (bot_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None
        elif bot_id is not None:
            cursor.execute(base_query + " WHERE bot_id = ?" + order_clause, (bot_id,))
            return [dict(row) for row in cursor.fetchall()]
        else:
            cursor.execute(base_query + " WHERE user_id = ?" + order_clause, (user_id,))
            return [dict(row) for row in cursor.fetchall()]


# 查询记录条数
def count_users():
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count


# 添加新记录
def add_record(type_id, count, field2, field3, field4, field5, field6, amount):
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO ys_data (type, count, field2, field3, field4, field5, field6, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (type_id, count, field2, float(field3), float(field4), float(field5), float(field6), int(amount)))
        conn.commit()
    return f"已添加：{type_id} 预设"


# 根据 type 删除记录
def delete_record(type_id):
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ys_data WHERE type = ?", (type_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return f"已删除：{type_id} 预设"
        else:
            return f"未找到：{type_id} 预设"


# 更新记录
def update_record(type_id, count=None, field2=None, field3=None, field4=None, field5=None, field6=None, amount=None):
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        updates = []
        params = []

        if count is not None:
            updates.append("count = ?")
            params.append(count)
        if field2 is not None:
            updates.append("field2 = ?")
            params.append(field2)
        if field3 is not None:
            updates.append("field3 = ?")
            params.append(float(field3))
        if field4 is not None:
            updates.append("field4 = ?")
            params.append(float(field4))
        if field5 is not None:
            updates.append("field5 = ?")
            params.append(float(field5))
        if field6 is not None:
            updates.append("field6 = ?")
            params.append(float(field6))
        if amount is not None:
            updates.append("amount = ?")
            params.append(int(amount))

        if updates:
            params.append(type_id)
            query = f"UPDATE ys_data SET {', '.join(updates)} WHERE type = ?"
            cursor.execute(query, params)
            conn.commit()
            if cursor.rowcount > 0:
                return f"已更新：{type_id} 预设"
            else:
                return f"未找到：{type_id} 预设"
        else:
            return "没有提供更新数据"


# 查询记录
def query_records(type_id=None):
    with sqlite3.connect(YS_DATA_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if type_id is None:
            cursor.execute("SELECT * FROM ys_data ORDER BY amount DESC")
            return [dict(row) for row in cursor.fetchall()]
        else:
            cursor.execute("SELECT * FROM ys_data WHERE type = ?", (type_id,))
            row = cursor.fetchone()
            return dict(row) if row else None


# 查询记录条数
def count_records():
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ys_data")
        count = cursor.fetchone()[0]
        return count
