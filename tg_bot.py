from enum import Enum
import logging

from environs import Env
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from redis import Redis


logger = logging.getLogger(__name__)


class STATES(Enum):
   NO_QUESTION = 1
   CHECK_ANSWER = 2


def reply_with_keyboard(reply_text, update):
    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text(
        reply_text,
        reply_markup=reply_markup,
    )


def start(update, redis_client):
    user = update.effective_user
    setup_new_user_storage = {
        'current_question_hash': '',
        'score': 0,
    }
    redis_client.hset(user.id, mapping=setup_new_user_storage)

    reply_text = f'Привет, {user.first_name}! Добро пожаловать на викторину. ' \
        f'Нажми на кнопку "Новый вопрос". ' \
        f'Для отмены игры набери /cancel'
    reply_with_keyboard(reply_text, update)

    logger.info(f'Новый пользователь {user.id} вступил в игру')

    return STATES.NO_QUESTION


def cancel(update, redis_client):
    user = update.message.from_user
    user_score = redis_client.hget(user.id, 'score')
    redis_client.delete(user.id)

    update.message.reply_text(
        f'Спасибо за игру! Вы заработали {user_score} очков.',
        reply_markup=ReplyKeyboardRemove()
    )

    logger.info(f'Пользователь {user.id} покинул игру, заработав {user_score} очков')

    return ConversationHandler.END


def ask_question(update, redis_client):
    user = update.effective_user

    random_question_hash = redis_client.srandmember('question_hashes')
    redis_client.hset(user.id, 'current_question_hash', random_question_hash)
    q_and_a = redis_client.hgetall(random_question_hash)

    reply_with_keyboard(q_and_a['question'], update)

    logger.debug(f'Пользователю {user.id} задан вопрос с id {random_question_hash}')

    return STATES.CHECK_ANSWER


def surrender(update, redis_client):
    user = update.effective_user
    question_hash = redis_client.hget(user.id, 'current_question_hash')
    q_and_a = redis_client.hgetall(question_hash)

    reply_text = f'Вот тебе правильный ответ: {q_and_a["full_answer"]}\n' \
                 f'Чтобы продолжить, нажми "Новый вопрос"'
    reply_with_keyboard(reply_text, update)

    logger.debug(f'Пользователь {user.id} сдался, не ответив на вопрос c id {question_hash}')

    return STATES.NO_QUESTION


def check_answer(update, redis_client):
    user = update.effective_user
    user_storage = redis_client.hgetall(user.id)
    q_and_a = redis_client.hgetall(user_storage['current_question_hash'])

    if update.message.text.strip().lower() == q_and_a['clean_answer']:
        redis_client.hset(user.id, 'score', int(user_storage['score']) + 1)

        reply_text = 'Правильно! Счет увеличен! Для следующего вопроса нажми "Новый вопрос"'
        reply_with_keyboard(reply_text, update)

        logger.debug(f'Пользователь {user.id} ответил верно '
                     f'на вопрос с id {user_storage["current_question_hash"]}')

        return STATES.NO_QUESTION
    else:
        reply_text = 'Неверно, попробуй еще раз'
        reply_with_keyboard(reply_text, update)

        logger.debug(f'Пользователь {user.id} ответил неверно '
                     f'на вопрос с id {user_storage["current_question_hash"]}')

        return STATES.CHECK_ANSWER


def get_score(update, redis_client):
    user = update.effective_user
    user_score = redis_client.hget(user.id, 'score')

    reply_text = f'Твой счет: {user_score} очков.'
    reply_with_keyboard(reply_text, update)

    logger.debug(f'Пользователь {user.id} запросил свой счет')


def send_error_message(update, _):
    reply_text = f'Вот сейчас не понял тебя :('
    reply_with_keyboard(reply_text, update)

    logger.debug(f'Пользователь ответил не по сценарию')


def run() -> None:
    env = Env()
    env.read_env()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info('Бот стартовал')

    updater = Updater(env('TG_TOKEN'))
    redis_client = Redis.from_url(env('REDIS'), decode_responses=True)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', lambda update, _: start(update, redis_client))],
        states={
            STATES.NO_QUESTION: [
                MessageHandler(
                    Filters.regex('^Новый вопрос$'),
                    lambda update, _: ask_question(update, redis_client),
                ),
            ],
            STATES.CHECK_ANSWER: [
                MessageHandler(
                    Filters.regex('^Сдаться$'),
                    lambda update, _: surrender(update, redis_client),
                ),
                MessageHandler(
                    Filters.text & (~ Filters.command),
                    lambda update, _: check_answer(update, redis_client),
                ),
            ],
        },
        fallbacks=[
            CommandHandler(
                'cancel',
                lambda update, _: cancel(update, redis_client),
            ),
            MessageHandler(
                Filters.regex('^Мой счет$'),
                lambda update, _: get_score(update, redis_client),
            ),
            MessageHandler(
                Filters.regex('^.+'),
                send_error_message,
            ),
        ],
    )

    updater.dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    run()
