def run():
    with open('qq/kaluga15.txt', 'r', encoding='koi8-r') as f:
        q_and_a = f.read().split('\n\n')

    question = answer = None
    for text_block in q_and_a:
        if text_block.startswith('Вопрос'):
            question = ' '.join(text_block.split('\n')[1:])
        elif text_block.startswith('Ответ:'):
            answer = text_block.split('\n')[1][:-1]
        if question and answer:
            print(f'quest: {question}', f'ans: {answer}', sep='\n', end='\n\n')
            question = answer = None


if __name__ == '__main__':
    run()
