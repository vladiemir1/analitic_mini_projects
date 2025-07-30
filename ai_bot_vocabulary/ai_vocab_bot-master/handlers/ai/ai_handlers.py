from os.path import split

from data.user_session import user_data
from data.create_empty import create_empty_user
from aiogram.filters import Command, Text
import filters.filters as f
from lexicon.lexicon_ru import LEXICON_RU
from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from classes.classes import Dictionary
from data.update_table import update
import psycopg2
import os
import os
import google.generativeai as genai
import re



router = Router()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

generation_config = {
  "temperature": 1.5,
  "top_p": 0.6,
  "top_k": 50,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}


def bold_words(text):
    # Ищем слова, обрамленные ** и заменяем их на <b>word</b>
    return re.sub(r'\*\*(\w+)\*\*', r'<b>\1</b>', text)

def check_goodbye_phrase(text):
    # Регулярное выражение для поиска фразы с учётом регистра первой буквы
    pattern = r'(?i)\bthanks for the conversation, goodbye\b'
    return bool(re.search(pattern, text))


model = genai.GenerativeModel("gemini-1.5-flash", generation_config=generation_config)

def get_prompt(mode, words):
    if mode==0:
        prompt = str("let's have a little conversation. try to use B2 words. " 
            f"in each subsequent message, you must use one of these words {words} in given order. start using these words by first message."
             "you should highlight this word. Also try to use these words in most common context. "
             f"after you response {len(words)} times,you have to stop conversation and "
             "say 'thanks for the conversation, goodbye'. "
            "messages should contain some question. after each of my answers, "
            "at first rate how my answer is logically related to your message, just by one number: 0 or 1"
             " and then generate your sentence. separate these parts by \n\n")
    else:
        prompt = ''
    return prompt


@router.callback_query(Text(text=['to_ai']))
async def proccess_welcome_ai(callback: CallbackQuery):
    update()
    user_id = callback.from_user.id
    db = psycopg2.connect(dbname=os.environ['POSTGRES_DB'],
                          user=os.environ['POSTGRES_USER'],
                          password=os.environ['POSTGRES_PASSWORD'],
                          host=os.environ['POSTGRES_CONTAINER_NAME'],  # Это имя контейнера с базой данных
                          port="5432")
    sql = db.cursor()
    sql.execute(f'SELECT set_test_words, ai_mode FROM users WHERE user_id={user_id}')
    count, mode = sql.fetchone()
    create_empty_user(user_id)
    sql.execute(f'SELECT en FROM words WHERE user_id={user_id} ORDER BY coef ASC LIMIT {count}')
    words = [x[0] for x in sql.fetchall()]
    sql.close()
    db.close()
    if len(words)==0:
        await callback.message.answer("Перед тем, как начинать пользоваться AI помощником, добавьте слов в свой словарь"
                                      "Выйти в /menu")
        await callback.answer()
    else:
        user_data[user_id]['chat'] = model.start_chat(history=[
                                                        {'role':'user',
                                                       'parts':get_prompt(mode, words)}
                                                      ])

        response = user_data[user_id]['chat'].send_message("Hello")
        await callback.message.answer("У вас включён режим <b>диалог с ИИ</b>. "
                                      "Постарайтесь вести непринуждённую беседу, отвечать на вопросы.\n"
                                      "В каждом сообщении ИИ будет использовать одно из слов вашего словаря, "
                                      "что поможет в закреплении новых слов. Удачи!:)")
        await callback.message.answer(bold_words(response.text))
        await callback.answer()
        user_data[user_id]['words'] = words
        user_data[user_id]['state'] = 'in_ai'
        user_data[user_id]['total'] = 0
        user_data[user_id]['correct'] = 0




@router.message(F.text,~Text(startswith='/'), f.InAiMode(user_data))
async def proccess_message_ai(message: Message):
    user_id = message.from_user.id
    response = user_data[user_id]['chat'].send_message(message.text)
    split_response = response.text.split('\n\n')
    user_data[user_id]['total'] += 1
    try:
        user_data[user_id]['correct'] += int(split_response[0])
    except ValueError:
        print(split_response[0])
        pass

    try:
        msg = bold_words(split_response[1])
    except IndexError:
        msg = bold_words(split_response[0])

    print(msg, msg.endswith('goodbye.'), msg[-6:])

    await message.answer(msg)

    if (check_goodbye_phrase(msg)
        or user_data[user_id]['total'] >= len(user_data[user_id]['words'])):
        
        user_data[user_id]['state'] = 'in_menu'
        rating_diff = 5*(2*user_data[user_id]['correct'] - user_data[user_id]['total'])
        await message.answer('Диалог успешно закончился!'
                            f'\nВаш результат: {rating_diff} рейтинга'
                             '\nВыйти в /menu')
        










