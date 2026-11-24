import logging
import os
import time

import requests
import vk_api
import uuid
from dotenv import load_dotenv
from vk_api.exceptions import ApiError

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
    """
    Проверяет наличие обязательных переменных окружения.
    Проверка отсутствия обязательных переменных
    окружения (уровень CRITICAL).
    """
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'VK_TOKEN': VK_TOKEN,
        'VK_USER_ID': VK_USER_ID,
    }
    missing = [name for name, value in tokens.items() if not value]
    if missing:
        logging.critical(
            f'Отсутствуют переменные окружения: {", ".join(missing)}'
        )
        raise ValueError('Критические переменные окружения не заданы')


def send_message(vk, message):
    """
    Отправляет сообщение.
    Удачная отправка любого сообщения в VK (уровень DEBUG).
    Сбой при отправке сообщения в VK (уровень ERROR).
    """
    if not message:
        return
    try:
        vk.messages.send(
            user_id=VK_USER_ID,
            message=message,
            random_id=uuid.uuid4().int,
        )
        logging.debug(f'Сообщение успешно отправлено: {message!r}')
    except ApiError as error:
        logging.error(f'Ошибка API VK: {error}', exc_info=True)
    except Exception as error:
        logging.error(f'Общая ошибка отправки: {error}', exc_info=True)


def get_api_answer(timestamp):
    """
    Запрашивает статусы домашних работ.
    Недоступность эндпоинта (уровень ERROR).
    Любые другие сбои при запросе к эндпоинту (уровень ERROR).
    """
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params, timeout=30
        )
    except requests.RequestException as error:
        raise ConnectionError(
            f'Эндпоинт {ENDPOINT} недоступен: {error}'
        ) from error

    if response.status_code != 200:
        raise ValueError(
            f'Эндпоинт {ENDPOINT} вернул код {response.status_code}: '
            f'{response.text}'
        )
    try:
        return response.json()
    except ValueError as error:
        raise ValueError(f'Ответ API не является JSON: {error}') from error


def check_response(response):
    """
    Проверяет структуру ответа и возвращает список домашних работ.
    Отсутствие ожидаемых ключей в ответе API (уровень ERROR).
    """
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API не является словарём: {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ "homeworks"')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            f'"homeworks" не является списком: {type(homeworks)}'
        )
    return homeworks


def parse_status(homework):
    """
    Возвращает текст сообщения о смене статуса домашней работы.
    Неожиданный статус домашней работы в ответе API (уровень ERROR).
    Отсутствие в ответе новых статусов (уровень DEBUG).
    """
    if 'homework_name' not in homework:
        raise KeyError('В ответе API отсутствует ключ "homework_name"')
    if 'status' not in homework:
        raise KeyError('В ответе API отсутствует ключ "status"')

    homework_name = homework['homework_name']
    status = homework['status']

    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise ValueError(f'Неожиданный статус домашней работы: {status!r}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()

    timestamp = int(time.time())
    last_error = None

    while True:
        try:
            response = get_api_answer(timestamp)
            # Получаем список работ
            homeworks = check_response(response)

            if not homeworks:
                logging.debug('В ответе API нет домашних работ.')
            else:
                for homework in homeworks:
                    try:
                        status_text = parse_status(homework)
                        send_message(vk, status_text)
                    except Exception as error:
                        logging.error(
                            f'{homework.get("homework_name")}: {error}'
                        )

            timestamp = int(time.time())
            last_error = None
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}', exc_info=True)
            error_text = f'{type(error).__name__}: {error}'
            if error_text != last_error:
                send_message(vk, f'Сбой в работе программы: {error}')
                last_error = error_text
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
