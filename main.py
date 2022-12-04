import sqlite3
import random
import requests
import telebot
import time
from telebot import types
import os
from dotenv import load_dotenv

load_dotenv(override=True)

bot = telebot.TeleBot(os.environ.get('TOKEN'))


def get_word_from_db(user_id):
    connection = sqlite3.connect('database/translatorDB.db')
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * from USER_WORDS where user_id={user_id} ORDER by negative DESC  limit 20")
        data = cursor.fetchall()
        random_from_dataset = random.randint(0, len(data) - 1)
        eng_words = data[random_from_dataset][1].split(',')
        rus_words = data[random_from_dataset][2].split(',')
        eng_word = eng_words[random.randint(0, len(eng_words) - 1)]
        return eng_word, rus_words
    except Exception as e:
        print(e)
        pass
    connection.commit()
    connection.close()


@bot.message_handler(commands=['workout'])
def workout(message, eng_word=None, rus_words=None):
    if eng_word is None and rus_words is None:
        eng_word, rus_words = get_word_from_db(message.chat.id)
    msg = bot.reply_to(message, f"Переведи слово: {eng_word}")
    bot.register_next_step_handler(msg, try_translate, eng_word, rus_words)


def try_translate(message, eng_word, rus_words):
    if message.text == 'stop':
        bot.send_message(message.chat.id, 'Закончили')
    elif message.text in rus_words:
        bot.send_message(message.chat.id, f'правильно')
        eng_word, rus_words = get_word_from_db(message.chat.id)
        workout(message, eng_word, rus_words)
    else:
        bot.send_message(message.chat.id, 'не правильно')
        eng_word, rus_words = get_word_from_db(message.chat.id)
        workout(message, eng_word, rus_words)


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


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    msg = message.text.split()
    if len(msg) > 1:
        answer, forward = get_translate_word_v1(message.text)
        if not answer:
            answer = 'Error1'
    else:
        answer, forward = get_translate_word_v1(message.text)
        if not answer:
            if forward == 'ru-en':
                src_lang = '1049'
                dst_lang = '1033'
            elif forward == 'en-ru':
                src_lang = '1033'
                dst_lang = '1049'
            answer = get_translate_word_v2(message.text, src_lang, dst_lang)
            if not answer:
                answer = 'Error2'
    if answer == 'Error1':
        bot.send_message(message.chat.id, 'Проблема с переводом фраз. попробуйте по одному слову')
    elif answer == 'Error2':
        bot.send_message(message.chat.id,
                         'Проблема с переводом сразу у двух сервисов, либо никто не знает такого слова.')
    else:
        bot.send_message(message.chat.id, answer)
        send_user_word(message.chat.id, forward, message.text, answer)
        print(f'добавляем {message.text} -> {answer}')


def get_translate_word_v2(word, src_lang, dst_lang):
    base_url = 'https://developers.lingvolive.com'
    auth_url = f'/api/v1/authenticate'
    headers = {
        'Authorization': f"Basic {os.environ.get('AUTHLINGUO')}"
    }
    auth = requests.post(url=base_url + auth_url, headers=headers)
    headers = {
        'Authorization': f"Bearer {auth.json()}"
    }
    mindcardurl = '/api/v1/Minicard'
    src_lang = f'&srcLang={src_lang}'
    dst_lang = f'&dstLang={dst_lang}'
    text = f'?text={word}'
    url = base_url + mindcardurl + text + src_lang + dst_lang
    check_word = requests.get(url=url, headers=headers)
    if check_word.status_code == 200:
        return check_word.json()['Translation']['Translation']
    else:
        return False


def get_language(symbol):
    en = False
    ru = False
    for i in symbol:
        test_code = ord(i)
        if 1040 <= test_code <= 1103:
            ru = True
        elif 65 <= test_code <= 122:
            en = True
    if ru and not en:
        return 'ru-en'
    elif en and not ru:
        return 'en-ru'
    elif en and ru:
        return False


def get_translate_word_v1(text):
    base = 'https://fasttranslator.herokuapp.com/api/v1/text/to/text'
    source = f'?source={text}'
    forward = get_language(text)
    if not forward:
        return 'У вас в сообщении буквы из двух языков. пожалуйста, напишите на каком нибудь одном.'
    else:
        lang = f'&lang={forward}'
        typeparam = '&as=json'
        url = base + source + lang + typeparam
        responce = requests.get(url)
        if responce.status_code == 200:
            return responce.json()['data'], forward
        else:
            return False, forward


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


def send_user_word(user_id, forward, message, translate):
    if forward == 'ru-en':
        rus_word = message
        eng_word = translate.replace(' ', '').replace(';', ',')
    elif forward == 'en-ru':
        eng_word = message
        rus_word = translate.replace(' ', '').replace(';', ',')
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
