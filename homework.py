import logging
import os
import requests
import sys
import time
import telegram

from dotenv import load_dotenv
from exceptions import ResponseError, SendMessageError, AnswerError

load_dotenv()

API_RESPONSE_ERROR = ('Значение кода возрата "{response}" '
                      'не соответствует требуемому - "200".')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}
RESPONSE_KEY_FAIL = 'Ключ homeworks не найден!'
RESPONSE_TYPE_FAIL = 'Неправильный тип для homeworks. Тип - {0}'
EMPTY_LIST = 'Список работ пуст.'
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
SUCCESSFUL_MSG_SENDING = 'Сообщение {message} успешно отправлено.'
STATUS_FAIL = 'Статус {0} не найден.'
MISSING_TOKEN = 'Нет токенов: {0}.'
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
SEND_MESSAGE_ERROR = ('Ошибка {error} при отправке сообщения '
                      '{message} в Telegram')
PROGRAMM_ERROR = 'Сбой в работе программы: {0}'
CHECK_TOKENS_ERROR = 'Запуск программы невозможен.'
VERDICT = 'Изменился статус проверки работы "{0}"-{1}'

path = os.getcwd()
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.expanduser(__file__ + '.log'),
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(SUCCESSFUL_MSG_SENDING.format(message=message))
    except Exception as error:
        raise SendMessageError(
            SEND_MESSAGE_ERROR.format(error=error, message=message))


def get_api_answer(current_timestamp):
    """Получение ответа от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        message = 'Запрос выполнить не удалось'
        raise AnswerError(message)
    if 'code' in response.json():
        raise ResponseError(f'{response: "code"}')
    if 'error' in response.json():
        raise ResponseError(f'{response: "error"}')
    if response.status_code != 200:
        raise ResponseError(
            API_RESPONSE_ERROR.format(response=response.status_code))
    response = response.json()
    return response


def check_response(response):
    """Проверка ответа API."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(RESPONSE_KEY_FAIL)
    if not isinstance(homeworks, list):
        raise TypeError(RESPONSE_TYPE_FAIL.format(type(homeworks)))
    if not homeworks:
        logger.info(EMPTY_LIST)
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
            logger.error(PROGRAMM_ERROR.format(error))
            send_message(bot, PROGRAMM_ERROR.format(error))
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
