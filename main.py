import sqlite3
import random
import requests
import telebot
from datetime import datetime
import time
from telebot import types
import os
from dotenv import load_dotenv

load_dotenv(override=True)
token = os.environ.get("AIMTOKEN")
token_data_expired = datetime.strptime(os.environ.get("AIMTOKENDATA"), '%Y-%m-%dT%H:%M:%S.%f')
test = os.environ.get("TEST")
bot = telebot.TeleBot(os.environ.get('TOKEN'))


# проверяем годность токена. если его нет или осталось меньше часа, получаем новый.

def get_aim_token(token, token_data_expired):
    if token_data_expired <= datetime.now():
        url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
        body = {
            "yandexPassportOauthToken": os.environ.get("YAAUTH")
        }
        result = requests.post(url, json=body)
        aim_token = result.json()['iamToken']
        aim_token_data_expired = datetime.strptime(result.json()['expiresAt'][0:26], '%Y-%m-%dT%H:%M:%S.%f')
        return aim_token, aim_token_data_expired
    else:
        return token, token_data_expired


def get_word_from_db(user_id):
    connection = sqlite3.connect('database/translatorDB.db')
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * from USER_WORDS where user_id={user_id} ORDER by negative DESC  limit 20")
        data = cursor.fetchall()
        random_from_dataset = random.randint(0, len(data) - 1)
        word_info = {
            "id": data[random_from_dataset][0],
            "eng": data[random_from_dataset][2],
            "rus": data[random_from_dataset][3],
            "positive": data[random_from_dataset][4],
            "negative": data[random_from_dataset][5],
            "count_try": data[random_from_dataset][6]
        }

        return word_info
    except Exception as e:
        print(e)
        pass
    connection.commit()
    connection.close()


@bot.message_handler(commands=['workout'])
def workout(message, word_info=None):
    if word_info is None:
        bot.send_message(message.chat.id, 'Режим тренировки, чтобы выйти введи stop')
        word_info = get_word_from_db(message.chat.id)
    msg = bot.reply_to(message, f'Переведи слово: {word_info["eng"]}')
    bot.register_next_step_handler(msg, try_translate, word_info)


def increace_pisitive(word_info, result):
    positive = f'UPDATE USER_WORDS SET positive={word_info["positive"] + 1},  count_try={word_info["count_try"] + 1} WHERE ID = {word_info["id"]}'
    negative = f'UPDATE USER_WORDS SET negative={word_info["negative"] + 1},  count_try={word_info["count_try"] + 1} WHERE ID = {word_info["id"]}'
    connection = sqlite3.connect('database/translatorDB.db')
    cursor = connection.cursor()
    if result == 'positive':
        cursor.execute(positive)
    else:
        cursor.execute(negative)
    connection.commit()
    connection.close()


def try_translate(message, word_info):
    if message.text == 'stop':
        bot.send_message(message.chat.id, 'Закончили')
    elif message.text.lower() in word_info["rus"].lower():
        bot.send_message(message.chat.id, f'правильно')
        increace_pisitive(word_info, "positive")
        word_info = get_word_from_db(message.chat.id)
        workout(message, word_info)
    else:
        bot.send_message(message.chat.id, f'не правильно, это: {word_info["rus"]}')
        increace_pisitive(word_info, "negative")
        word_info = get_word_from_db(message.chat.id)
        workout(message, word_info)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    usinfo = (message.from_user.id,
              message.from_user.username,
              message.from_user.first_name,
              message.from_user.last_name,
              time.ctime()
              )
    send_user_info(usinfo)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("/workout")
    markup.add(btn1)
    bot.send_message(message.chat.id,
                     text="Привет, {0.first_name}! я помогатор в переводе слов. просто напиши слово на "
                          "английском или на русском, я переведу.".format(
                         message.from_user), reply_markup=markup)


def get_translate_from_ya(text, direction):
    global token
    global token_data_expired
    aim_token, aim_token_data_expired = get_aim_token(token, token_data_expired)
    token = aim_token
    token_data_expired = aim_token_data_expired
    url = 'https://translate.api.cloud.yandex.net/translate/v2/translate'
    body = {
        "targetLanguageCode": direction,
        "texts": text,
        "folderId": os.environ.get('FOLDERID'),
    }
    headers = {
        "Authorization": f"Bearer {aim_token}"
    }
    result = requests.post(url, headers=headers, json=body)
    if result.status_code == 200:
        return result.json()["translations"][0]["text"]
    else:
        return f"Ошибка: {result.status_code}"


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if (len(message.text.split()) > 10) or (len(message.text) > 50):
        bot.send_message(message.chat.id, "Мы тут слова и короткие фразы переводим, а не вот это вот всё")
    else:
        direction = get_direction_translate(message.text)
        if direction:
            answer = get_translate_from_ya(message.text, direction)
            bot.send_message(message.chat.id, answer)
            send_user_word(message.chat.id, direction, message.text, answer)
        else:
            bot.send_message(message.chat.id, "Ошибка при определении направления перевода")


def get_direction_translate(symbol):
    en = False
    ru = False
    for i in symbol:
        test_code = ord(i)
        if 1040 <= test_code <= 1103:
            ru = True
        elif 65 <= test_code <= 122:
            en = True
    if ru and not en:
        return 'en'
    elif en and not ru:
        return 'ru'
    elif en and ru:
        return False


def create_user_table(connect):
    with connect as connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS  USERS_BOT (user_id INTEGER NOT NULL PRIMARY KEY,username TEXT,"
                f"first_name TEXT,last_name TEXT,reg_date DATE)")
            connection.commit()
            cursor.execute(
                f'CREATE TABLE IF NOT EXISTS  USER_WORDS (id INTEGER NOT NULL UNIQUE, user_id INTEGER NOT NULL, eng_word TEXT,'
                f'rus_word TEXT,positive INTEGER,negative INTEGER, count_try INTEGER, PRIMARY KEY("id" AUTOINCREMENT))')
            connection.commit()
        except Exception as err:
            print(err)


def init_base():
    try:
        sqlite_connection = sqlite3.connect('database/translatorDB.db')
        create_user_table(sqlite_connection)
        sqlite_connection.commit()
        sqlite_connection.close()

    except sqlite3.Error as error:
        print("Ошибка при подключении к sqlite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("Соединение с SQLite закрыто")


def send_user_info(usinfo):
    connection = sqlite3.connect('database/translatorDB.db')
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"INSERT INTO USERS_BOT (user_id, username, first_name, last_name, reg_date) "
            f"VALUES({usinfo[0]},'{usinfo[1]}','{usinfo[2]}','{usinfo[3]}','{usinfo[4]}')")
    except Exception as e:
        print(e)
        pass
    connection.commit()
    connection.close()


def send_user_word(user_id, direction, message, translate):
    if direction == 'en':
        rus_word = message
        eng_word = translate
    elif direction == 'ru':
        eng_word = message
        rus_word = translate
    connection = sqlite3.connect('database/translatorDB.db')
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"INSERT INTO USER_WORDS (user_id, eng_word, rus_word, positive, negative, count_try) "
            f"VALUES('{user_id}','{eng_word}','{rus_word}',0,0,0)")
    except Exception as e:
        print(e)
        pass
    connection.commit()
    connection.close()


if __name__ == '__main__':
    init_base()
    bot.infinity_polling()
