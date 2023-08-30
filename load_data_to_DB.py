import argparse
import logging
import os

from environs import Env
from redis import Redis

LAST_QUESTION_ID = 0

logger = logging.getLogger(__name__)


def read_args():
    parser = argparse.ArgumentParser(
        description='''
            Tool for load questions and answers from .txt files to Redis DB
        '''
    )
    parser.add_argument(
        '--path',
        required=True,
        type=str,
        help='Path to folder with .txt files with q&a'
    )

    args = parser.parse_args()
    return args


def parse_file_content(file_content):
    question = answer = None
    q_and_a = []
    for text_block in file_content.split('\n\n'):
        if text_block.startswith('Вопрос'):
            question = ' '.join(text_block.split('\n')[1:])
        elif text_block.startswith('Ответ:'):
            answer = text_block.split('\n')[1][:-1]
        if question and answer:
            q_and_a.append({
                'question': question,
                'answer': answer,
            })
            question = answer = None
    return q_and_a


def run():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    logger.info('Start parsing...')

    env = Env()
    env.read_env()

    args = read_args()

    redis_client = Redis.from_url(env('REDIS'), decode_responses=True)
    logger.info('Connected to redis')

    question_id = LAST_QUESTION_ID
    filepaths = []
    for root, _, filenames in os.walk(args.path, topdown=False):
        filepaths = (os.path.join(root, file) for file in filenames)

    logger.info(f'Found {len(filepaths)} .txt files')

    for filepath in filepaths:
        with open(filepath, 'r', encoding='koi8-r') as f:
            file_content = f.read()
        q_and_a_pairs = parse_file_content(file_content)
        logger.info(f'Found {len(q_and_a_pairs)} q&a in {filepath} file, load it to redis')
        for q_and_a_pair in q_and_a_pairs:
            redis_client.hmset(f'q{question_id}', q_and_a_pair)
            question_id += 1

        logger.info(f'Loading from {filepath} file complete, taking another file')


if __name__ == '__main__':
    run()
