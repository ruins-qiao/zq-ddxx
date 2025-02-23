import variable
import config
from collections import defaultdict
import asyncio
import re
import json
import os
import random


async def zq_user(client, event):
    my = event.raw_text.split(" ")
    if "st" == my[0]:
        variable.continuous = int(variable.ys[my[1]][0])
        variable.lose_stop = int(variable.ys[my[1]][1])
        variable.lose_once = float(variable.ys[my[1]][2])
        variable.lose_twice = float(variable.ys[my[1]][3])
        variable.lose_three = float(variable.ys[my[1]][4])
        variable.lose_four = float(variable.ys[my[1]][5])
        variable.initial_amount = int(variable.ys[my[1]][6])
        mes = f"""启动\n{variable.ys[my[1]]}"""
        message = await client.send_message(config.user, mes, parse_mode="markdown")
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
        asyncio.create_task(delete_later(client, message.chat_id, message.id, 10))
        return
    if "res" == my[0]:
        # variable.history = []
        variable.win_total = 0
        variable.total = 0
        variable.earnings = 0
        mes = f"""重置成功"""
        message = await client.send_message(config.user, mes, parse_mode="markdown")
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
        asyncio.create_task(delete_later(client, message.chat_id, message.id, 10))
        return
    if "set" == my[0]:
        variable.explode = int(my[1])
        variable.profit = int(my[2])
        variable.stop = int(my[3])
        variable.stop_count = int(my[3])
        mes = f"""设置成功"""
        message = await client.send_message(config.user, mes, parse_mode="markdown")
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
        asyncio.create_task(delete_later(client, message.chat_id, message.id, 10))
        return
    if "ms" == my[0]:
        variable.mode = int(my[1])
        mes = f"""设置成功"""
        message = await client.send_message(config.user, mes, parse_mode="markdown")
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
        asyncio.create_task(delete_later(client, message.chat_id, message.id, 10))
        return
    if "open" == my[0]:
        variable.open_ydx = True
        await client.send_message(config.group, '/ydx')
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
        return
    if "off" == my[0]:
        variable.open_ydx = False
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
        return
    if "xx" == my[0]:
        group = [-1002262543959, -1001833464786]
        for g in group:
            messages = [msg.id async for msg in client.iter_messages(g, from_user='me')]
            await client.delete_messages(g, messages)
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 3))
        return
    if "top" == my[0]:
        # 获取本地文件
        dat = load_data_from_file()
        # 根据bot_id 获取相应站点用户集合
        sorted_data = sorted(dat.get(str(config.zq_bot)), key=lambda x: x['amount'], reverse=True)
        # 生成捐赠榜文本
        donation_list = f"```当前{config.name}个人总榜Top: 20 为\n"
        # 添加总榜 Top 5
        for i, item in enumerate(sorted_data[:20], start=1):
            name = item['name']
            count = item['count']
            amount = item['amount']
            count1 = item['-count']
            amount1 = item['-amount']
            donation_list += f"     总榜Top {i}: {name} 大佬共赏赐小弟: {count} 次,共计: {format_number(int(amount))} 爱心\n     {config.name} 共赏赐 {name} 小弟： {count1} 次,共计： {format_number(int(amount1))} 爱心\n"
        donation_list += f"```"
        message = await client.send_message(config.user, donation_list)
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 60))
        asyncio.create_task(delete_later(client, message.chat_id, message.id, 60))
        return
    if "ys" == my[0]:
        ys = [int(my[2]), int(my[3]), float(my[4]), float(my[5]), float(my[6]), float(my[7]), int(my[8])]
        variable.ys[my[1]] = ys
        mes = """设置成功"""
        message = await client.send_message(config.user, mes, parse_mode="markdown")
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
        asyncio.create_task(delete_later(client, message.chat_id, message.id, 10))
        return
    if "yss" == my[0]:
        if len(my) > 1:
            if "dl" == my[1]:
                del variable.ys[my[2]]
                mes = """删除成功"""
                message = await client.send_message(config.user, mes, parse_mode="markdown")
                asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
                asyncio.create_task(delete_later(client, message.chat_id, message.id, 10))
        if len(variable.ys) > 0:
            max_key_length = max(len(str(k)) for k in variable.ys.keys())
            mes = "\n".join(
                f"'{k.ljust(max_key_length)}': {v}" for k, v in variable.ys.items())
            message = await client.send_message(config.user, mes, parse_mode="markdown")
            asyncio.create_task(delete_later(client, event.chat_id, event.id, 60))
            asyncio.create_task(delete_later(client, message.chat_id, message.id, 60))
        else:
            mes = """暂无预设"""
            message = await client.send_message(config.user, mes, parse_mode="markdown")
            asyncio.create_task(delete_later(client, event.chat_id, event.id, 10))
            asyncio.create_task(delete_later(client, message.chat_id, message.id, 10))
        return


async def zq_bet_on(client, event):
    await asyncio.sleep(5)
    if variable.bet_on or (variable.mode and variable.mode_stop) or (variable.mode == 2 and variable.mode_stop):
        # 判断是否是开盘信息
        if event.reply_markup:
            print(f"开始押注！")
            # 获取压大还是小
            if variable.mode == 1:
                check = predict_next_combined_trend(variable.history)
            elif variable.mode == 0:
                check = predict_next_trend(variable.history)
            else:
                check = chase_next_trend(variable.history)
            print(f"本次押注：{check}")
            # 获取押注金额 根据连胜局数和底价进行计算
            variable.bet_amount = calculate_bet_amount(variable.win_count, variable.lose_count,
                                                       variable.initial_amount,
                                                       variable.lose_stop, variable.lose_once, variable.lose_twice,
                                                       variable.lose_three, variable.lose_four)
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
                await client.send_message(config.user, mes, parse_mode="markdown")
                variable.mark = True
            else:
                if variable.mark:
                    variable.explode_count += 1
                    print("触发停止押注")
                    variable.mark = False
                variable.bet = False
    else:
        variable.bet = False


def predict_next_combined_trend(history):
    """
    长短期趋势结合 获取押注大小
    """
    if len(history) < 10:
        return random.choice([0, 1])

    short_term = sum(history[-3:])
    long_term = sum(history[-10:])
    if short_term >= 2 and long_term >= 6:
        return 1
    elif short_term <= 1 and long_term <= 4:
        return 0
    else:
        return random.choice([0, 1])


def chase_next_trend(history):
    """
    追投
    """
    if len(history) < 1:
        return random.choice([0, 1])

    return 1 if history[-1] else 0


def predict_next_trend(history):
    return 0 if history[-1] else 1


def calculate_bet_amount(win_count, lose_count, initial_amount, lose_stop, lose_once, lose_twice, lose_three,
                         lose_four):
    if win_count >= 0 and lose_count == 0:
        return closest_multiple_of_500(initial_amount)
    else:
        if (lose_count + 1) > lose_stop:
            return 0
        if lose_count == 1:
            return closest_multiple_of_500(variable.bet_amount * lose_once + (variable.bet_amount * lose_once * 0.01))
        if lose_count == 2:
            return closest_multiple_of_500(variable.bet_amount * lose_twice + (variable.bet_amount * lose_twice * 0.01))
        if lose_count == 3:
            return closest_multiple_of_500(variable.bet_amount * lose_three + (variable.bet_amount * lose_three * 0.01))
        if lose_count >= 4:
            return closest_multiple_of_500(variable.bet_amount * lose_four + (variable.bet_amount * lose_four * 0.01))


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
        print(f"{event.pattern_match.group(1)}")
        print(f"{event.pattern_match.group(2)}")
        if variable.open_ydx:
            await client.send_message(config.group, '/ydx')
        # 存储历史记录
        if len(variable.history) >= 1000:
            del variable.history[:5]
        if event.pattern_match.group(2) == variable.consequence:
            variable.win_times += 1
            variable.lose_times = 0
            variable.history.append(1 if event.pattern_match.group(2) == variable.consequence else 0)
        else:
            variable.win_times = 0
            variable.lose_times += 1
            variable.history.append(1 if event.pattern_match.group(2) == variable.consequence else 0)
        # 统计连大连小次数
        whether_bet_on(variable.win_times, variable.lose_times)

        if variable.bet:
            if event.pattern_match.group(2) == variable.consequence:
                if variable.bet_type == 1:
                    variable.win_total += 1
                    variable.earnings += (int(variable.bet_amount * 0.99))
                    variable.period_profit += (int(variable.bet_amount * 0.99))
                    variable.win_count += 1
                    variable.lose_count = 0
                    variable.status = 1
                else:
                    variable.earnings -= variable.bet_amount
                    variable.period_profit -= variable.bet_amount
                    variable.win_count = 0
                    variable.lose_count += 1
                    variable.status = 0
            else:
                if variable.bet_type == 0:
                    variable.win_total += 1
                    variable.earnings += (int(variable.bet_amount * 0.99))
                    variable.period_profit += (int(variable.bet_amount * 0.99))
                    variable.win_count += 1
                    variable.lose_count = 0
                    variable.status = 1
                else:
                    variable.earnings -= variable.bet_amount
                    variable.period_profit -= variable.bet_amount
                    variable.win_count = 0
                    variable.lose_count += 1
                    variable.status = 0

            # if variable.message2 is not None:
            #     await variable.message2.delete()
            # 发送相关信息
        #     mes = f"""
        #             **🎯 押注次数：{variable.total}
        # 🏆 胜率：{variable.win_total / variable.total * 100:.2f}%
        # 💰 收益：{variable.earnings}**
        #             """
        #     variable.message2 = await client.send_message(config.user, mes, parse_mode="markdown")
        #
        #     mes = f"""
        #             **📉 输赢统计： {"赢" if status else "输"} {int(variable.bet_amount * 0.99) if status else variable.bet_amount}
        # 🎲 结果： {event.pattern_match.group(2)}**
        #             """
        #     await client.send_message(config.user, mes, parse_mode="markdown")

        if variable.explode_count >= variable.explode or variable.period_profit >= variable.profit:
            if variable.stop_count > 1:
                variable.stop_count -= 1
                variable.bet_on = False
                variable.mode_stop = False
                mes = f"""还剩 {variable.stop_count} 局恢复押注"""
                message = await client.send_message('me', mes, parse_mode="markdown")
                asyncio.create_task(delete_later(client, message.chat_id, message.id, 30))
            else:
                variable.explode_count = 0
                variable.period_profit = 0
                variable.stop_count = variable.stop
                variable.mode_stop = True
                variable.win_count = 0
                variable.lose_count = 0
                mes = f"""恢复押注"""
                message = await client.send_message('me', mes, parse_mode="markdown")
                asyncio.create_task(delete_later(client, message.chat_id, message.id, 30))
        if variable.message is not None:
            await variable.message.delete()
        # 获取统计结果
        if len(variable.history) > 3:
            if len(variable.history) % 5 == 0:
                if variable.message1 is not None:
                    await variable.message1.delete()
                if variable.message3 is not None:
                    await variable.message3.delete()
                result_counts = count_consecutive(variable.history)
                # 创建消息
                mes = f"""
                📊 **最近 1000 局：**
🔴 **连“小”结果：**
{format_counts(result_counts["小"], "小")}
🟢 **连“大”结果：**
{format_counts(result_counts["大"], "大")}
                """
                variable.message1 = await client.send_message(config.user, mes, parse_mode="markdown")
                result_counts = count_consecutive(variable.history[-200::])
                # 创建消息
                mes = f"""
                📊 **最近 200 局：**
🔴 **连“小”结果：**
{format_counts(result_counts["小"], "小")}
🟢 **连“大”结果：**
{format_counts(result_counts["大"], "大")}
                 """
                variable.message3 = await client.send_message(config.user, mes, parse_mode="markdown")
        reversed_data = ["✅" if x == 1 else "❌" for x in variable.history[-40::][::-1]]  # 倒序列表
        mes = f"""
        📊 **近期 40 次结果**（由近及远）\n✅：大（1）  ❌：小（0）\n{os.linesep.join(
            " ".join(map(str, reversed_data[i:i + 10]))
            for i in range(0, len(reversed_data), 10)
        )}\n\n———————————————\n🎯 **策略设定**\n"""
        if variable.mode == 0:
            mes += f"""🎰 **押注模式 反投**\n"""
        elif variable.mode == 1:
            mes += f"""🎰 **押注模式 预测**\n"""
        else:
            mes += f"""🎰 **押注模式 追投**\n"""
        mes += f"""💰 **初始金额**：{variable.initial_amount}\n🔄 **{variable.continuous} 连反压**\n"""
        mes += f"""⏹ **押 {variable.lose_stop} 次停止**\n"""
        mes += f"""💥 **炸 {variable.explode} 次暂停 {variable.stop} 局**\n"""
        mes += f"""📈 **盈利限制 {variable.profit} / {variable.period_profit} 暂停 {variable.stop} 局**\n📉 **押注倍率 {variable.lose_once} / {variable.lose_twice} / {variable.lose_three} / {variable.lose_four}**\n\n"""
        if variable.bet:
            if variable.message2 is not None:
                await variable.message2.delete()
            mess = f"""**🎯 押注次数：{variable.total}\n🏆 胜率：{variable.win_total / variable.total * 100:.2f}%\n💰 收益：{variable.earnings}**"""
            variable.message2 = await client.send_message(config.user, mess, parse_mode="markdown")
            mess = f"""**📉 输赢统计： {"赢" if variable.status else "输"} {int(variable.bet_amount * 0.99) if variable.status else variable.bet_amount}\n🎲 结果： {event.pattern_match.group(2)}**"""
            await client.send_message(config.user, mess, parse_mode="markdown")
        variable.message = await client.send_message(config.user, mes, parse_mode="markdown")
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
                                await client.send_message(config.user, f"🎉 抢到红包{bonus}灵石！")
                                print("你成功领取了灵石！")
                                return
                            elif re.search("不能重复领取", response.message):
                                # 匹配 "不能重复领取"
                                await client.send_message(config.user, f"⚠️ 抢到红包，但是没有获取到灵石数量！")
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
                if match:
                    amount = match.group(1)
                # 获取本地文件
                dat = load_data_from_file()
                # 根据bot_id 获取相应站点用户集合
                ls = dat.get(str(event.sender_id))
                user = {}
                if ls is not None:
                    if len(ls) > 0:
                        t = True
                        for l in ls:
                            if l["id"] == user_id:
                                l["name"] = user_name
                                l["-amount"] += int(amount)
                                l["-count"] = l["-count"] + 1
                                l["amount"] = l["amount"]
                                l["count"] = l["count"]
                                user = l
                                t = False
                        if t:
                            user = {"id": user_id, "name": user_name, "amount": 0, "count": 0, "-amount": int(amount),
                                    "-count": 1}
                            dat[str(event.sender_id)].append(user)
                    else:
                        user = {"id": user_id, "name": user_name, "amount": 0, "count": 0, "-amount": int(amount),
                                "-count": 1}
                        dat[str(event.sender_id)] = [user]
                else:
                    user = {"id": user_id, "name": user_name, "amount": 0, "count": 0, "-amount": int(amount),
                            "-count": 1}
                    dat[str(event.sender_id)] = [user]
                a = {}
                save_data_to_file(a, "data.json")
                save_data_to_file(dat, "data.json")
                donation_list = f"大哥赏了你 {user["-count"]} 次 一共 {format_number(user["-amount"])} 爱心！\n 这可是我的血汗钱，别乱花哦"
                ms = await client.send_message(event.chat_id, donation_list, reply_to=message2.id)
                await asyncio.sleep(20)
                await ms.delete()
        # 获取上一条消息的回复（即上一条消息的上一条）
        if message1.reply_to_msg_id:
            message2 = await client.get_messages(event.chat_id, ids=message1.reply_to_msg_id)
            if message2.from_id.user_id == config.user:
                # 获取大佬的id
                user_id = message1.sender.id
                user_name = message1.sender.first_name
                match = re.search(r"\+(\d+)", message1.raw_text)
                if match:
                    amount = match.group(1)
                print(f"收到来自他人的转账人id:{user_id}  名称：{user_name}   金额：{amount}")
                # 获取本地文件
                dat = load_data_from_file()
                # 根据bot_id 获取相应站点用户集合
                ls = dat.get(str(event.sender_id))
                user = {}
                if ls is not None:
                    if len(ls) > 0:
                        t = True
                        for l in ls:
                            if l["id"] == user_id:
                                l["name"] = user_name
                                l["amount"] += int(amount)
                                l["count"] = l["count"] + 1
                                l["-amount"] = l["-amount"]
                                l["-count"] = l["-count"]
                                user = l
                                t = False
                        if t:
                            user = {"id": user_id, "name": user_name, "amount": int(amount), "count": 1,
                                    "-amount": 0, "-count": 0}
                            dat[str(event.sender_id)].append(user)
                    else:
                        user = {"id": user_id, "name": user_name, "amount": int(amount), "count": 1,
                                "-amount": 0, "-count": 0}
                        dat[str(event.sender_id)] = [user]
                else:
                    user = {"id": user_id, "name": user_name, "amount": int(amount), "count": 1, "-amount": 0,
                            "-count": 0}
                    dat[str(event.sender_id)] = [user]
                a = {}
                save_data_to_file(a, "data.json")
                save_data_to_file(dat, "data.json")

                sorted_data = sorted(dat.get(str(event.sender_id)), key=lambda x: x['amount'], reverse=True)
                index = next((i for i, item in enumerate(sorted_data) if item["id"] == user["id"]), -1)
                # 计算捐赠池总额
                total_amount = sum(int(item['amount']) for item in dat.get(str(event.sender_id)))
                # 生成捐赠榜文本
                donation_list = f"```感谢 {user_name} 大佬赏赐的: {format_number(int(amount))} 爱心\n"
                donation_list += f"大佬您共赏赐了小弟: {user["count"]} 次,共计: {format_number(user["amount"])} 爱心\n"
                donation_list += f"您是{config.name}个人打赏总榜的Top: {index + 1}\n\n"
                donation_list += f"当前{config.name}个人总榜Top: 5 为\n"
                # 添加总榜 Top 5
                for i, item in enumerate(sorted_data[:5], start=1):
                    name = item['name']
                    count = item['count']
                    am = item['amount']
                    donation_list += f"     总榜Top {i}: {mask_if_less(int(amount), config.top, name)} 大佬共赏赐小弟: {mask_if_less(int(amount), config.top, count)} 次,共计: {mask_if_less(int(amount), config.top, format_number(int(am)))} 爱心\n"
                donation_list += f"\n单次打赏>={format_number(config.top)}魔力查看打赏榜，感谢大佬，并期待您的下次打赏\n"
                donation_list += f"小弟给大佬您共孝敬了: {user["-count"]} 次,共计: {format_number(user["-amount"])} 爱心"
                donation_list += f"\n二狗哥出品，必属精品```"
                ms = await client.send_message(event.chat_id, donation_list, reply_to=message1.id)
                await asyncio.sleep(20)
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


# 初始数据结构
data = {
}


# 将数据保存到 JSON 文件
def save_data_to_file(data, filename='data.json'):
    """将数据保存到 JSON 文件中"""
    with open(filename, 'w') as f:
        # 使用 json.dump() 方法将数据保存为 JSON 格式
        json.dump(data, f, indent=4)
    print(f"数据已保存到 {filename}")


# 从 JSON 文件加载数据
def load_data_from_file(filename='data.json'):
    """从 JSON 文件加载数据"""
    if not os.path.exists(filename):  # 如果文件不存在，返回初始数据
        print(f"文件 {filename} 未找到，使用初始数据")
        return data

    try:
        with open(filename, 'r') as f:
            loaded_data = json.load(f)
            if not loaded_data:  # 如果文件为空，返回初始数据
                print(f"文件 {filename} 为空，使用初始数据")
                return data
            return loaded_data
    except json.JSONDecodeError:
        print(f"文件 {filename} 格式错误，使用初始数据")
        return data
