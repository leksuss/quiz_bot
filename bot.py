import logging

from environs import Env
from telegram import Update, ForceReply, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from redis import Redis

MAX_TRIES_COUNT = 3

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


def start(update, redis_client):
    user = update.effective_user
    setup_new_user_storage = {
        'current_question': '',
        'tries_count': 1,
        'score': 0,
    }
    redis_client.hset(user.id, mapping=setup_new_user_storage)

    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_markdown_v2(
        f'Привет, {user.mention_markdown_v2()}\! Добро пожаловать на викторину\. '
        f'У тебя на каждый вопрос только {MAX_TRIES_COUNT} попытки\. Чтобы начать, '
        f'нажми на кнопку "Новый вопрос"\.',
        reply_markup=reply_markup,
    )


def cancel(update, _):
    update.message.reply_text('Help!')


def send_reply(update, redis_client):
    user_id = update.effective_user.id
    user_storage = redis_client.hgetall(user_id)
    reply_text = ''
    if user_storage['current_question']:
        q_and_a = redis_client.hgetall(user_storage['current_question'])
        if update.message.text.strip().lower() == q_and_a['clean_answer'].lower():
            redis_client.hset(
                user_id,
                mapping={
                    'current_question': '',
                    'tries_count': 1,
                    'score': int(user_storage['score']) + 2,
                }
            )
            reply_text = 'Правильно! Твой счет +2! Для следующего вопроса нажми "Новый вопрос"'
        elif int(user_storage['tries_count']) < MAX_TRIES_COUNT:

            reply_text = f'Неправильно :( Попробуй еще раз, у тебя осталось ' \
                         f'{MAX_TRIES_COUNT - int(user_storage["tries_count"])} попытки'
            redis_client.hset(user_id, 'tries_count', int(user_storage['tries_count']) + 1)
        elif int(user_storage['tries_count']) == MAX_TRIES_COUNT:
            redis_client.hset(
                user_id,
                mapping={
                    'current_question': '',
                    'tries_count': 1,
                    'score': int(user_storage['score']) - 2,
                }
            )
            reply_text = 'У тебя не осталось попыток, твой счет -2, нажми на "Новый вопрос"'
    elif update.message.text == 'Новый вопрос':
        random_question_hash = redis_client.srandmember('question_hashes')
        q_and_a = redis_client.hgetall(random_question_hash)
        redis_client.hset(user_id, 'current_question', random_question_hash)
        reply_text = q_and_a['question']
    elif update.message.text == 'Сдаться':
        q_and_a = redis_client.hgetall(user_storage['current_question'])
        redis_client.hset(
            user_id,
            mapping={
                'current_question': '',
                'tries_count': 1,
                'score': int(user_storage['score']) - 1,
            }
        )
        reply_text = f'Твой счет понижен на 1. ' \
                     f'Вот тебе правильный ответ: \n{q_and_a["full_answer"]}.\n\n' \
                     'Чтобы продолжить, нажми "Новый вопрос"'
    elif update.message.text == 'Мой счет':
        reply_text = f'Твой счет: {user_storage["score"]}'
    else:
        reply_text = 'Вот сейчас не совсем понятно было. Нажми на одну из кнопок ниже.'

    custom_keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text(reply_text, reply_markup=reply_markup)


def run() -> None:
    env = Env()
    env.read_env()

    updater = Updater(env('TG_TOKEN'))
    redis_client = Redis.from_url(env('REDIS'), decode_responses=True)

    updater.dispatcher.add_handler(
        CommandHandler(
            'start',
            lambda update, _: start(update, redis_client),
        )
    )
    updater.dispatcher.add_handler(
        CommandHandler(
            'cancel',
            lambda update, _: start(update, redis_client),
        )
    )

    updater.dispatcher.add_handler(
        MessageHandler(
            Filters.text & ~Filters.command,
            lambda update, _: send_reply(update, redis_client)
        )
    )

    updater.start_polling()
    updater.idle()



if __name__ == '__main__':
    run()
