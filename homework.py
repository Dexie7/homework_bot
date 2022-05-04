import logging
import os
import sys
import time
from xmlrpc.client import ResponseError

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


path = os.getcwd()
logging.basicConfig(
    level=logging.DEBUG,
    filename=os.path.join(path, 'main.log'),
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        chat_id = TELEGRAM_CHAT_ID
        text = message
        bot.send_message(chat_id, text)
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Получение ответа от API."""
    try:
        timestamp = current_timestamp or int(time.time())
        if not isinstance(timestamp, (float, int)):
            raise TypeError('Ошибка формата даты')
        params = {'from_date': timestamp}
        hw_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response = hw_statuses.json()
        if hw_statuses.status_code == 200:
            return response
        else:
            response_error = response.get('error')
            response_code = response.get('code')
            if response_error:
                logging.error(f'Ошибка при обращении к API {response_error}')
                raise ResponseError(f'Ошибка запроса API {response_error}')
            elif response_code:
                logging.error(f'Ошибка при обращении к API {response_code}')
                raise ResponseError(f'Ошибка запроса API {response_code}')
            else:
                logging.error('Нет ответа от API')
                raise ResponseError('Нет ответа от API')
    except Exception as error:
        raise logging.error(f'Ошибка при обращении к API: {error}')


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка типа данных в response')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Ошибка типа данных переменной homeworks')
    if len(homeworks) != 0:
        return homeworks
    else:
        raise IndexError('Список работ пуст')


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('Ошибка типа данных переменной homework')
    if not homework['homework_name']:
        logging.error('Отсутствие ключа homework_name в ответе API')
        raise KeyError('Отсутствие ключа homework_name в ответе API')
    if not homework['status']:
        logging.error('Отсутствие ключа status в ответе API')
        raise KeyError('Отсутствие ключа status в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
    else:
        logging.error('Недокументированный статус домашней работы')
        raise AttributeError('Недокументированный статус домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    tokens = True
    tokens_check = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for tk in tokens_check:
        if tk is None:
            tokens = False
            logging.critical(f'Ошибка токена {tk}')
        return tokens


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        raise logging.critical('Ошибка токенов')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.debug('Бот запущен')
    current_timestamp = int(time.time()) - RETRY_TIME
    temp_error = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            current_timestamp = response.get(
                'current_date', current_timestamp
            )
            for hw in homework:
                message = parse_status(hw)
                send_message(bot, message)
            logging.info('Сообщение отправлено')
        except IndexError:
            logging.debug('Список работ пуст')
        except Exception as error:
            if temp_error is None:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                temp_error = error
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
