import sqlite3
from utils import NUMBER_OF_TASKS, ADMIN_RATE, DELTA_RATE


conn = sqlite3.connect("bd.db")

cursor = conn.cursor()


class User:
    def __init__(self, vk_id):
        self.vk_id = vk_id
        self.rate = 0  # рейтинг пользователя в системе
        self.status = 2  # уровень прав: 2 - обычный пользователь, 1 - админ (может добавлять подсказки)
        self.progress = {}  # прогресс по задачам
        for tmp_task in range(NUMBER_OF_TASKS):
            self.progress[str(tmp_task + 1)] = 1  # начальный прогресс по каждой задаче равен 1
        self.state = 0  # состояние переписки
        self.problem = 1  # номер запрошенной пользователем задачи
        self.vk_id = str(self.vk_id)
        cursor.execute("SELECT vk_id FROM User")
        all_user_id = map(lambda qwe: qwe[0], cursor.fetchall())  # список id всех имеющихся в базе данных пользователей
        if self.vk_id not in all_user_id:  # если пользователя нет в базе данных, то добавляем его
            tmp_progress = ''
            for tmp_task in range(NUMBER_OF_TASKS):
                tmp_progress+=str(tmp_task + 1) + "-1;"
            cursor.execute("insert into User values('{vk_id}','{rate}','{progress}','{status}')"
                           .format(vk_id=self.vk_id,
                                   rate='0',
                                   progress=tmp_progress,
                                   status='2'))
        else:  # иначе достаем оттуда данные о нем
            cursor.execute("SELECT PROGRESS FROM User where vk_id="+self.vk_id)
            num_pro = cursor.fetchall()[0][0].split(';')  # список пар вида: номер_задачи-прогресс
            bd_progress = {}
            for pair in num_pro:
                if '-' in pair:
                    pair = pair.split('-')
                    bd_progress[pair[0]] = pair[1]
            self.progress = bd_progress
            cursor.execute("SELECT rate FROM User where vk_id=" + self.vk_id)
            self.rate = cursor.fetchall()[0][0]
            if int(self.rate) >= ADMIN_RATE:  # если пользователь достиг пороговый рейтинг, то
                self.status = 1  # делаем его админом
        conn.commit()

    # метод, изменяющий состояние переписки и сохраняющий номер запрашиваемой пользователем задачи
    def change_state(self, state, problem=None):
        self.state = state
        if problem is not None:
            self.problem = problem

    def change_rate(self):  # метод, редактирующий рейтинг пользователя
        self.rate = str(int(self.rate) + DELTA_RATE)
        self.vk_id = str(self.vk_id)
        cursor.execute("SELECT rate FROM User where vk_id=" + self.vk_id)
        user_rate = int(cursor.fetchall()[0][0]) + DELTA_RATE
        cursor.execute("UPDATE User SET rate="+str(user_rate)+" where vk_id=" + self.vk_id)
        conn.commit()
        if int(self.rate) >= ADMIN_RATE:
            self.status = 1

    def change_progress(self, problem):  # метод, редактирующий прогресс пользователя
        problem = str(problem)
        self.progress[problem] = str(int(self.progress[problem]) + 1)  # увеличиваем прогресс по данной задаче
        cursor.execute("SELECT progress FROM User where vk_id=" + self.vk_id)
        num_pro = cursor.fetchall()[0][0].split(';')
        bd_progress = {}
        for pair in num_pro:
            if '-' in pair:
                pair = pair.split('-')
                bd_progress[pair[0]] = pair[1]
        bd_progress[problem] = str(int(bd_progress[problem]) + 1)
        load_progress = ''
        for tmp_problem in bd_progress:
            load_progress += tmp_problem + "-" + bd_progress[tmp_problem] + ";"
        cursor.execute("UPDATE User SET progress='" + load_progress + "' where vk_id='" + self.vk_id + "'")
        conn.commit()

    def get_level(self):
        return self.progress[str(self.problem)]

    def add_hint(self, problem, text, question, answer):
        cursor.execute("SELECT PROBLEM FROM Hint")
        problems_list = list(map(lambda q: str(q + 1), range(NUMBER_OF_TASKS)))
        cursor.execute("SELECT count(level) FROM Hint where problem=" + str(problem))
        level = str(int(cursor.fetchall()[0][0]) + 1)  # увеличиваем уровень подсказки на 1
        if problem in problems_list:
            cursor.execute("insert into Hint values('{problem}','{level}','{question}','{answer}','{text}')"
                           .format(problem=problem,
                                   level=level,
                                   question=question.capitalize(),
                                   answer=answer.capitalize(),
                                   text=text.capitalize()))
        conn.commit()
