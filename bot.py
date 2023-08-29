from environs import Env


def run():
    env = Env()
    env.read_env()



if __name__ == '__main__':
    run()