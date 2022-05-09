import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import JsonError, WrongStatus

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}
MESSAGE_FAIL = 'Сообщение {0} не отправлено: {1}.'
RESPONSE_KEY_FAIL = 'Ключ homeworks не найден!'
RESPONSE_TYPE_FAIL = 'Неправильный тип для homeworks. Тип - {0}'
RETRY_TIME = 600
TIMEOUT = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
SERVER_ERROR = 'Ошибка сервера. {0}, URL{1},Headers{2}, Params{3}, Timeout{4}'
SUCCESSFUL_MESSAGE_SENDING = 'Сообщение {message} успешно отправлено.'
STATUS_FAIL = 'Статус {0} не найден.'
MESSAGE = 'Ответ не является словарем!'
MISSING_TOKEN = 'Нет токенов: {0}.'
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
RESPONSE_ERROR = 'Отказ от обслуживания. {0}, {1}, {2}, {3}, {4}'
PROGRAMM_ERROR = 'Сбой в работе программы: {0}'
CHECK_TOKENS_ERROR = 'Запуск программы невозможен. Произошла ошибка токенов'
VERDICT = 'Изменился статус проверки работы "{0}"-{1}'

logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + '.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(SUCCESSFUL_MESSAGE_SENDING.format(message=message))
    except telegram.TelegramError as error:
        logger.exception(MESSAGE_FAIL.format(message, error))


def get_api_answer(current_timestamp):
    """Получение ответа от API."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params,
                                timeout=TIMEOUT)
    except requests.RequestException as error:
        raise ConnectionError(SERVER_ERROR.format(
            error, ENDPOINT, HEADERS, params, TIMEOUT))
    if response.status_code != HTTPStatus.OK:
        raise WrongStatus(SERVER_ERROR.format(
            response.status_code, ENDPOINT, HEADERS, params, TIMEOUT))
    answer = response.json()
    for error in ['code', 'error']:
        if error in answer:
            raise JsonError(RESPONSE_ERROR.format(
                answer[error], ENDPOINT, HEADERS, params, TIMEOUT))
    return answer


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(MESSAGE.format(response))
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(RESPONSE_KEY_FAIL)
    if not isinstance(homeworks, list):
        raise TypeError(RESPONSE_TYPE_FAIL.format(type(homeworks)))
    return homeworks


def parse_status(homework):
    """Проверка статуса домашней работы."""
    name = homework['homework_name']
    status = homework['status']
    if status in HOMEWORK_STATUSES:
        return VERDICT.format(name, HOMEWORK_STATUSES[status])
    raise ValueError(STATUS_FAIL.format(status))


def check_tokens():
    """Проверка токенов."""
    lost_tokens = [token for token in TOKENS if globals()[token] is None]
    if lost_tokens:
        logger.error(MISSING_TOKEN.format(lost_tokens))
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise RuntimeError(CHECK_TOKENS_ERROR)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            current_timestamp = response.get(
                'current_date', current_timestamp)
        except Exception as error:
            send_message(bot, PROGRAMM_ERROR.format(error))
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
