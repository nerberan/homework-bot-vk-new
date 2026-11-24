import os
from dotenv import load_dotenv
import requests
import logging
import vk_api
import time

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
VK_TOKEN = os.getenv('VK_TOKEN')
VK_USER_ID = os.getenv('VK_USER_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def check_tokens():
    if not PRACTICUM_TOKEN or not VK_TOKEN or not VK_USER_ID:
        raise ValueError('Ошибка при запросе к переменной окружения')


def send_message(vk, message):
    if not message:
        return
    try:
        vk.messages.send(
            user_id=VK_USER_ID,
            message=message,
        )
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения в VK: {error}')



def get_api_answer(timestamp):
    response = requests.get(
        ENDPOINT,
        headers={'Authorization': PRACTICUM_TOKEN},
        params={'timestamp': timestamp}
    )
    return response.json()


def check_response(response):
    homeworks = response.get('homeworks', [])
    if not homeworks:
        return None
    status = homeworks[0].get('status')
    if status is None:
        return None
    return HOMEWORK_VERDICTS.get(status)


def parse_status(homework):
    status = homework.get('status')
    if status is None:
        return None
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        return None
    homework_name = homework.get('homework_name', 'неизвестная работа')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'



def main():
    """Основная логика работы бота."""

    check_tokens()

    # Создаем сессию для бота
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    timestamp = int(time.time())

    ...

    while True: 
        try: 
            response = get_api_answer(timestamp)
            status_text = parse_status(response.get('homeworks', [{}])[0]) 
            if status_text: 
                send_message(vk, status_text)
                timestamp = int(time.time())
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            send_message(vk, f'Сбой в работе программы: {error}')
            time.sleep(60) 


if __name__ == '__main__':
    main()
