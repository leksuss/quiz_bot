import argparse
import hashlib
import logging
import os

from environs import Env
from redis import Redis

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


def get_cleaned_answer(answer):
    answer = answer.strip('". ').lower()
    return min(answer.split('.')[0], answer.split('(')[0], key=len)


def run():
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s %(message)s'))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info('Start parsing...')

    env = Env()
    env.read_env()

    args = read_args()

    redis_client = Redis.from_url(env('REDIS'), decode_responses=True)
    logger.info('Connected to redis')

    filepaths = []
    for root, _, filenames in os.walk(args.path, topdown=False):
        filepaths = [os.path.join(root, file) for file in filenames]

    logger.info(f'Found {len(filepaths)} txt files')

    for filepath in filepaths:
        count_added = 0
        with open(filepath, 'r', encoding='koi8-r') as f:
            file_content = f.read()
        q_and_a_pairs = parse_file_content(file_content)

        logger.info(f'Found {len(q_and_a_pairs)} q&a in {filepath} file, load it to redis')

        for q_and_a_pair in q_and_a_pairs:

            q_hash = hashlib.md5(q_and_a_pair['question'].encode()).hexdigest()
            if not redis_client.sismember('question_hashes', q_hash):
                redis_client.sadd('question_hashes', q_hash)
                redis_client.hset(
                    q_hash,
                    mapping={
                        'question': q_and_a_pair['question'],
                        'full_answer': q_and_a_pair['answer'],
                        'clean_answer': get_cleaned_answer(q_and_a_pair['answer']),
                    },
                )
                count_added += 1

        logger.info(f'Loading from {filepath} file complete, added {count_added} q&a')

    logger.info(f'Loading to DB complete')


if __name__ == '__main__':
    run()
