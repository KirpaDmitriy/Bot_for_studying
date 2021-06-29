from traceback import format_exc
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import random
from user import User
import sqlite3
from utils import *

conn = sqlite3.connect("bd.db")  # подключаемся к базе данных

cursor = conn.cursor()
hints_data = {}  # данные о подсказках

conn.commit()


# загружаем подсказки из базы данных
def load_hints():
    global hints_data
    cursor.execute("SELECT * FROM Hint")
    f = cursor.fetchall()
    for w in f:
        if w[0] in hints_data:
            hints_data[w[0]][w[1]]={
                'question':w[2],
                'answer':w[3],
                'text':w[4]
            }
        else:
            hints_data[w[0]]={}
            hints_data[w[0]][w[1]] = {
                'question': w[2],
                'answer': w[3],
                'text': w[4]
            }


# проверяем, является ли аргумент числом
def is_int(string):
    try:
        int(string)
        return True
    except ValueError:
        return False


def message(vk_id, message_text, photo=''):
    vk.method('messages.send', {'user_id': vk_id,
                                'message': message_text,
                                'attachment': photo,
                                'random_id': random.randint(1, 2048)})


def sticker(vk_id, sticker_id):
    vk.method('messages.send', {'user_id': vk_id,
                                'sticker_id': sticker_id,
                                'random_id': random.randint(1, 2048)})


# проверка на sql-инъекцию
def sql_check(string):
    string = ''.join(string.split())
    if ("'" in string) or ("--" in string) or ("/*" in string):
        return False
    return True


load_hints()
users = {}  # словарь пользователей в текущей сессии
problems_numbers = list(map(lambda q:str(q+1), range(NUMBER_OF_TASKS)))  # номера всех задач

BREAK, HELP, NUMBERS, ADD = COMMANDS

vk = vk_api.VkApi(token=TOKEN)  # получаем доступ
longpoll = VkLongPoll(vk)  # получаем доступ

while True:  # если внутри цикла выпадет исключение, то программа все равно продолжит работу
    try:
        for event in longpoll.listen():  # ждем сообщения о событиях в вконтакте
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:
                    if event.user_id not in users:  # если пользователь в данной сессии появляется впервые, то
                        users[event.user_id] = User(event.user_id)  # добавляем его в словарь пользователей
                    current_user = users[event.user_id]  # текущий пользователь
                    request = event.text  # сообщение пользователя
                    if is_int(request):
                        if users[event.user_id].state == 0:  # бот получает номер задачи
                            if request in problems_numbers:  # если введеная задача имеется в autocode
                                try:
                                    # переводим бота в режим получения ответов на вопрос, сохраняем номер задачи
                                    users[event.user_id].change_state(1, int(request))
                                    send_question = hints_data[str(current_user.problem)][str(current_user.get_level())]["question"]
                                    message(event.user_id, random.choice([SEND_QUESTION_1, SEND_QUESTION_2]) + send_question)
                                except KeyError:
                                    message(event.user_id, random.choice([NO_HINTS_1, NO_HINTS_2]))
                                    users[event.user_id].change_state(0)  # переводим бота в режим ожидания задачи
                            else:  # задачи нет в autocode
                                message(event.user_id, INCORRECT_PROBLEM)
                                users[event.user_id].change_state(0)  # переводим бота в режим ожидания задачи
                        elif users[event.user_id].state == 1:  # бот получает ответ на контрольный вопрос
                            if str(request) != hints_data[str(current_user.problem)][str(current_user.get_level())]["answer"]:  # если ответ неправильный, то...
                                podskazka = hints_data[str(current_user.problem)][str(current_user.get_level())]["text"]  # достаем текст подсказки
                                sticker(event.user_id, PLAYING_DOG)
                                message(event.user_id, SEND_HINT + podskazka)
                                message(event.user_id, NEW_PROBLEM)
                                users[event.user_id].change_state(0)
                            else:  # ответ верный
                                message(event.user_id, PRAISE)
                                sticker(event.user_id, SUPER_CAT)
                                users[event.user_id].change_rate()
                                users[event.user_id].change_progress(users[event.user_id].problem)  # меняем прогресс по данной задаче
                                try:
                                    current_user=users[event.user_id]  # обновляем данные о текущем пользователе
                                    send_question = hints_data[str(current_user.problem)][str(current_user.get_level())]["question"]
                                    message(event.user_id, random.choice([SEND_QUESTION_1, SEND_QUESTION_2]) +
                                            send_question)
                                    users[event.user_id].change_state(1)
                                except KeyError:
                                    message(event.user_id, random.choice([NO_HINTS_1, NO_HINTS_2]))
                                    users[event.user_id].change_state(0)
                    elif request.lower()[0:3] == ADD:  # пользователь отправил запрос на добавление подсказки
                        if current_user.status == 1:  # если пользователь - админ
                            req = request.lower().split(DELIMITER)  # в качестве разделителя в запросе используется нижнее
                            if len(req) == 5:  # формат операции подразумевает наличие 5 блоков в запросе (первый из них - название каманды)
                                problem = req[1]  # номер задачи
                                text = req[2]  # текст подсказки
                                question = req[3]  # контрольный вопрос
                                answer = req[4]  # ответ на контрольный вопрос
                                if is_int(problem) and is_int(answer) and (problem in problems_numbers) and sql_check(text + question):  # если строка правильного формата, то...
                                    current_user.add_hint(problem, text, question, answer)
                                    load_hints()
                                    message(event.user_id, ADDED_NEW_HINT)
                                    sticker(event.user_id, KISSING_CAT)
                                else:  # иначе сообщаем об ошибке
                                    message(event.user_id, TANKS)
                            else:  # если неверный формат, то...
                                message(event.user_id, TANKS)
                        else:  # если пользователь не админ
                            message(event.user_id, PERM_DENIED, GENDALF)
                    elif request.lower() == BREAK:  # если пользователь запросил ввод задачи
                        message(event.user_id, NEW_PROBLEM_1)
                        users[event.user_id].change_state(0)
                    elif request.lower() == HELP:  # пользователь запросил помощь
                        message(event.user_id, TANKS_1)
                        users[event.user_id].change_state(0)
                    elif request.lower() == NUMBERS:  # пользователь запросил список задач
                        message(event.user_id, NUM_AND_PROBLEMS)
                        users[event.user_id].change_state(0)
                    else:  # некорректный ввод
                        message(event.user_id, NEED_HELP)
                        sticker(event.user_id, ANGRY_CAT)
                        users[event.user_id].change_state(0)
    except Exception:  # если произошла ошибка, то
        print(format_exc())  # выводим сообщение о ней в консоль
