import asyncio
from collections import defaultdict

import variable
import config
import os


def whether_bet_on(win_times, lose_times):
    if win_times >= variable.continuous or lose_times >= variable.continuous and len(
            variable.history) >= variable.continuous:
        variable.bet_on = True
    else:
        variable.bet_on = False
        variable.win_count = 0
        variable.lose_count = 0


async def bet_on(event, message, client):
    await asyncio.sleep(5)
    if variable.bet_on:
        # 判断是否是开盘信息
        if message == variable.start_betting:
            if event.reply_markup:
                print(f"开始押注！")
                # 获取压大还是小
                check = predict_next_trend(variable.history)
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
                    ⚡ 押注： {"押大" if check else "押小"}
💵 金额： {variable.bet_amount}
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


async def handle_settlement_message(message, client):
    if message[0:8] == variable.settle:
        if variable.open_ydx:
            await client.send_message(config.group, '/ydx')
            await asyncio.sleep(2)
            await message.delete()
        # 存储历史记录
        if len(variable.history) >= 1000:
            del variable.history[:5]
        if message[:-2:-1] == variable.consequence:
            variable.win_times += 1
            variable.lose_times = 0
            variable.history.append(1 if message[:-2:-1] == variable.consequence else 0)
        else:
            variable.win_times = 0
            variable.lose_times += 1
            variable.history.append(1 if message[:-2:-1] == variable.consequence else 0)
        # 统计连大连小次数
        whether_bet_on(variable.win_times, variable.lose_times)
        if variable.explode_count >= variable.explode:
            if variable.stop_count > 1:
                variable.stop_count -= 1
                variable.bet_on = False
                mes = f"""还剩 {variable.stop_count} 局恢复押注"""
                m = await client.send_message('me', mes, parse_mode="markdown")
                await asyncio.sleep(20)
                await m.delete()
            else:
                variable.explode_count = 0
                variable.stop_count = variable.stop
                variable.win_count = 0
                variable.lose_count = 0
                mes = f"""恢复押注"""
                m = await client.send_message('me', mes, parse_mode="markdown")
                await asyncio.sleep(20)
                await m.delete()
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
                📊 **最近 {len(result_counts)} 局：**
🔴 **连“小”结果：**
{format_counts(result_counts["小"], "小")}
🟢 **连“大”结果：**
{format_counts(result_counts["大"], "大")}
                """
                variable.message1 = await client.send_message(config.user, mes, parse_mode="markdown")
                result_counts = count_consecutive(variable.history[-200::])
                # 创建消息
                mes = f"""
                📊 **最近 {len(result_counts)} 局：**
🔴 **连“小”结果：**
{format_counts(result_counts["小"], "小")}
🟢 **连“大”结果：**
{format_counts(result_counts["大"], "大")}
                """
                variable.message3 = await client.send_message(config.user, mes, parse_mode="markdown")
        print(f"近20次结果：{variable.history[::-1]}")
        reversed_data = ["✅" if x == 1 else "❌" for x in variable.history[-40::][::-1]]  # 倒序列表
        mes = f"""
        📊 **近期 40 次结果**（由近及远）  
✅：大（1）  ❌：小（0）
{os.linesep.join(
            " ".join(map(str, reversed_data[i:i + 10]))
            for i in range(0, len(reversed_data), 10)
        )}

———————————————
🎯 **策略设定**  
💰 **初始金额**：{variable.initial_amount}  
🔄 **{variable.continuous}连反压**  
⏹ **押 {variable.lose_stop} 次停止**  
💥 **炸 {variable.explode} 次暂停**  
🚫 **暂停 {variable.stop} 局**  
📉 **输 1 次：倍数 {variable.lose_once}**
📉 **输 2 次：倍数 {variable.lose_twice}**
📉 **输 3 次：倍数 {variable.lose_three}**
📉 **输 4 次：倍数 {variable.lose_four}**
        """
        variable.message = await client.send_message(config.user, mes, parse_mode="markdown")
        # 根据是否押注来统计 胜率和押注局数
        if variable.bet:
            if message[:-2:-1] == variable.consequence:
                if variable.bet_type == 1:
                    variable.win_total += 1
                    variable.earnings += (int(variable.bet_amount * 0.99))
                    variable.win_count += 1
                    variable.lose_count = 0
                    status = 1
                else:
                    variable.earnings -= variable.bet_amount
                    variable.win_count = 0
                    variable.lose_count += 1
                    status = 0
            else:
                if variable.bet_type == 0:
                    variable.win_total += 1
                    variable.earnings += (int(variable.bet_amount * 0.99))
                    variable.win_count += 1
                    variable.lose_count = 0
                    status = 1
                else:
                    variable.earnings -= variable.bet_amount
                    variable.win_count = 0
                    variable.lose_count += 1
                    status = 0

            # 发送相关信息
            if status:
                mes = f"""
                🎲 结果： {message[:-2:-1]}
📉 输赢统计： 赢 {int(variable.bet_amount * 0.99)}
                """
            else:
                mes = f"""
                🎲 结果： {message[:-2:-1]}
📉 输赢统计： 输 {variable.bet_amount}
                """
            await client.send_message('me', mes, parse_mode="markdown")
            if variable.message2 is not None:
                await variable.message2.delete()
            mes = f"""
            🎯 押注次数：{variable.total}
🏆 胜率：{variable.win_total / variable.total * 100:.2f}%
💰 收益：{variable.earnings}
            """
            variable.message2 = await client.send_message(config.user, mes, parse_mode="markdown")


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
            return closest_multiple_of_500(variable.bet_amount * lose_once)
        if lose_count >= 2:
            return closest_multiple_of_500(variable.bet_amount * lose_twice)
        if lose_count == 3:
            return closest_multiple_of_500(variable.bet_amount * lose_three)
        if lose_count >= 4:
            return closest_multiple_of_500(variable.bet_amount * lose_four)


async def handle_red_packet_message(event, client):
    message = event.raw_text[0:3]
    if variable.red_packet == message:
        if event.reply_markup:
            await event.click(0)
            for m in message:
                await event.click(0)
            for m in message:
                await asyncio.sleep(1)
                await event.click(0)
            for m in message:
                await asyncio.sleep(1)
                await event.click(0)
            for m in message:
                await asyncio.sleep(1)
                await event.click(0)
            for m in message:
                await asyncio.sleep(2)
                await event.click(0)


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


async def handle_user_message(event, client):
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
        await asyncio.sleep(10)
        m = event.message
        await m.delete()
        await message.delete()
    if "res" == my[0]:
        # variable.history = []
        variable.win_total = 0
        variable.total = 0
        variable.earnings = 0
        mes = f"""重置成功"""
        message = await client.send_message(config.user, mes, parse_mode="markdown")
        m = event.message
        await asyncio.sleep(10)
        await m.delete()
        await message.delete()
    if "set" == my[0]:
        variable.explode = int(my[1])
        variable.stop = int(my[2])
        variable.stop_count = int(my[2])
        mes = f"""设置成功"""
        message = await client.send_message(config.user, mes, parse_mode="markdown")
        await asyncio.sleep(10)
        m = event.message
        await m.delete()
        await message.delete()
    if "open" == my[0]:
        variable.open_ydx = True
        message = event.message
        await message.delete()
        await client.send_message(config.group, '/ydx')
    if "off" == my[0]:
        variable.open_ydx = False
        message = event.message
        await message.delete()
    if "xx" == my[0]:
        group = [-1002262543959, -1001833464786]
        for g in group:
            messages = [msg.id async for msg in client.iter_messages(g, from_user='me')]
            await client.delete_messages(g, messages)
    if "ys" == my[0]:
        ys = [int(my[2]), int(my[3]), float(my[4]), float(my[5]), float(my[6]), float(my[7]), int(my[8])]
        variable.ys[my[1]] = ys
        mes = """设置成功"""
        message = await client.send_message(config.user, mes, parse_mode="markdown")
        m = event.message
        await asyncio.sleep(10)
        await m.delete()
        await message.delete()
        print("触发预设")
    if "yss" == my[0]:
        if len(my) > 1:
            if "dl" == my[1]:
                del variable.ys[my[2]]
                mes = """删除成功"""
                message = await client.send_message(config.user, mes, parse_mode="markdown")
                m = event.message
                await asyncio.sleep(5)
                await m.delete()
                await message.delete()
        if len(variable.ys) > 0:
            max_key_length = max(len(str(k)) for k in variable.ys.keys())
            mes = "\n".join(
                f"'{k.ljust(max_key_length)}': {v}" for k, v in variable.ys.items())
            message = await client.send_message(config.user, mes, parse_mode="markdown")
            m = event.message
            await asyncio.sleep(30)
            await m.delete()
            await message.delete()
        else:
            mes = """暂无预设"""
            message = await client.send_message(config.user, mes, parse_mode="markdown")
            m = event.message
            await asyncio.sleep(10)
            await m.delete()
            await message.delete()
