# Quiz bot

This is a couple of simple bots working in [VK](https://vk.com/) and [Telegram](https://telegram.org/). They are made for quiz. Questions and answers are uploaded to NoSQL DB Redis.   

And you can try this yourself, here is links of working bots:
 - [VK bot](https://vk.com/im?sel=-219218073)
 - [TG bot](https://t.me/sstorage_bot)

## Requirements

 - python3.6+
 - `python-telegram-bot`
 - `environs`
 - `redis`
 - `vk_api`

## How to setup

Bot interacts with VK and Telegram. So, you need to get access to it's API:

 - [create telegram bot](https://core.telegram.org/bots#how-do-i-create-a-bot) and receive token;
 - [create VK group](https://vk.com/groups?tab=admin), receive token and allow community to receive messages from users.

Use above information for fill settings in `.env` file. You can use `.env_example` as a template. Here is short description of each param:
```
TG_TOKEN - telegram help bot token
VK_TOKEN - vk help bot token
REDIS - redis configuration URL
```
[Here is](https://redis-py.readthedocs.io/en/stable/connections.html#redis.Redis.from_url) an examples of redis URL config

## How to upload questions and answer in Redis database?

Just run this script with `--path` param representing path to .txt files.
```python
python3 load_data_to_DB.py --path "path/to/folder/with/q&a"
```

TXT files with questions and answers should consist of structures like:
```
Вопрос:
Включение в турнир этого вопроса обосновано тем, что Майорку часто
называют семнадцатой федеральной землей Германии.
   Первое собрание основанного в 1950 году Средиземноморского Клуба
прошло на Майорке. Какая формулировка из двух английских слов стала
популярной после этого?

Ответ:
All Inclusive.
```

### How to run

Get the source code of this repo:
```bash
git clone git@github.com:leksuss/quiz_bot.git
```

Go inside folder:
```bash
cd quiz_bot
```

Python3 should be already installed. Then use pip (or pip3, if there is a conflict with Python2) to install dependencies:
```bash
# If you would like to install dependencies inside virtual environment, you should create it first.
pip3 install -r requirements.txt
```

And then run both bots, each in separate console:
```python
python3 tg_bot.py
```
and
```python
python3 vk_bot.py
```

## Goals
This project is made for study purpose.
