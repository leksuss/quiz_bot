import logging
import random

from environs import Env
from redis import Redis
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard


logger = logging.getLogger(__name__)


def draw_keyboard():
    keyboard = VkKeyboard()
    keyboard.add_button('Новый вопрос')
    keyboard.add_button('Сдаться')
    keyboard.add_line()
    keyboard.add_button('Мой счет')
    return keyboard.get_keyboard()


def set_welcome_state(event, redis_client):
    setup_new_user_storage = {
        'current_question_hash': '',
        'score': 0,
    }
    redis_client.hset(event.user_id, mapping=setup_new_user_storage)
    reply_text = f'Привет! Добро пожаловать на викторину. ' \
                 f'Нажми на кнопку "Новый вопрос". ' \
                 f'Для отмены игры набери /cancel',

    logger.info(f'Новый пользователь {event.user_id} вступил в игру')

    return reply_text


def ask_question_state(event, redis_client):
    random_question_hash = redis_client.srandmember('question_hashes')
    redis_client.hset(event.user_id, 'current_question_hash', random_question_hash)
    q_and_a = redis_client.hgetall(random_question_hash)
    reply_text = q_and_a['question']

    logger.debug(f'Пользователю {event.user_id} задан вопрос с id {random_question_hash}')

    return reply_text


def surrender_state(event, redis_client, user_storage):
    q_and_a = redis_client.hgetall(user_storage['current_question_hash'])
    redis_client.hset(event.user_id, 'current_question_hash', '')
    reply_text = f'Вот тебе правильный ответ: {q_and_a["full_answer"]}\n' \
                 'Чтобы продолжить, нажми "Новый вопрос"'

    logger.debug(
        f'Пользователь {event.user_id} сдался, не ответив на вопрос c id {user_storage["current_question_hash"]}')

    return reply_text


def cancel_quiz_state(event, redis_client, user_storage):
    reply_text = f'Спасибо за игру! Вы заработали {user_storage["score"]} очков.'
    redis_client.delete(event.user_id)

    logger.info(f'Пользователь {event.user_id} покинул игру, заработав {user_storage["score"]} очков')

    return reply_text


def check_answer_state(event, redis_client, user_storage):
    q_and_a = redis_client.hgetall(user_storage['current_question_hash'])
    if event.text.strip().lower() == q_and_a['clean_answer']:
        redis_client.hset(event.user_id, 'score', int(user_storage['score']) + 1)
        redis_client.hset(event.user_id, 'current_question_hash', '')
        reply_text = 'Правильно! Счет увеличен! Для следующего вопроса нажми "Новый вопрос"'
        logger.debug(f'Пользователь {event.user_id} ответил верно '
                     f'на вопрос с id {user_storage["current_question_hash"]}')
    else:
        reply_text = 'Неверно, попробуй еще раз'
        logger.debug(f'Пользователь {event.user_id} ответил неверно '
                     f'на вопрос с id {user_storage["current_question_hash"]}')
    return reply_text


def send_reply(event, bot, redis_client):
    user_storage = redis_client.hgetall(event.user_id)

    if not user_storage:
        reply_text = set_welcome_state(event, redis_client)

    elif event.text == 'Новый вопрос' and not user_storage['current_question_hash']:
        reply_text = ask_question_state(event, redis_client)

    elif event.text == 'Сдаться' and user_storage['current_question_hash']:
        reply_text = surrender_state(event, redis_client, user_storage)

    elif event.text == '/cancel':
        reply_text = cancel_quiz_state(event, redis_client, user_storage)

    elif event.text == 'Мой счет':
        reply_text = f'Твой счет: {user_storage["score"]} очков.'
        logger.debug(f'Пользователь {event.user_id} запросил свой счет')

    elif user_storage['current_question_hash']:
        reply_text = check_answer_state(event, redis_client, user_storage)

    else:
        reply_text = f'Вот сейчас не понял тебя :('
        logger.debug(f'Пользователь ответил не по сценарию')

    if reply_text:
        bot.messages.send(
            user_id=event.user_id,
            message=reply_text,
            keyboard=draw_keyboard(),
            random_id=random.randint(1,1000),
        )


def main():
    env = Env()
    env.read_env()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    vk_session = vk_api.VkApi(token=env('VK_TOKEN'))
    bot = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    redis_client = Redis.from_url(env('REDIS'), decode_responses=True)

    logger.info('Бот vk_bot стартовал')

    try:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                send_reply(event, bot, redis_client)
    except Exception as e:
        logger.exception(e)


if __name__ == "__main__":
    main()
