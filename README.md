# ddxx

# 仅用于学习交流使用！

个人小白自学 大佬勿喷

## 主要特性

自定义telegram客户端，处理群组消息实现特定功能

## 安装使用 
```bash
docker run -d --name my-telegram-bot --restart always \
  -e API_ID='你的API_ID' \
  -e API_HASH='你的API_HASH' \
  -e USER_SESSION='user_session' \
  -e GROUP_IDS='-1001234567,-1007654321' \
  -e ZQ_GROUP_IDS='-1008888888,-1009999999' \
  -e ZQ_BOT='机器人的数字ID' \
  -e USER_ID='你的Telegram用户数字ID' \
  -e NAME='自定义的统计名称' \
  -e TOP='1000' \
  -e ZHUQUE_COOKIE='服务Cookie' \
  -e ZHUQUE_X_CSRF='服务X-Csrf-Token' \
  -e ZHUQUE_API_URL='API的URL地址' \
  your-image-name:latest
```
