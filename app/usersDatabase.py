import json


class UserDatabase:
    def __init__(self, filename="users.json"):
        self.filename = filename
        self.load_users()

    def load_users(self):
        """Загрузка пользователей из файла"""
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                self.users = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.users = {}

    def save_users(self):
        """Сохранение пользователей в файл"""
        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(self.users, file, indent=4, ensure_ascii=False)

    def add_user(
        self,
        user_id,
        name,
        tg_name,
        tg_username,
        is_agree,
        is_mentoring,
        is_new,
        diagnostics_quantity,
    ):
        """Добавление пользователя в базу"""
        if str(user_id) not in self.users:
            self.users[str(user_id)] = {
                "user_id": user_id,
                "name": name,
                "tg_name": tg_name,
                "tg_username": tg_username,
                "is_agree": is_agree,
                "is_mentoring": is_mentoring,
                "is_new": is_new,
                "diagnostics_quantity": diagnostics_quantity,
            }
            self.save_users()

    def update_user_param(self, user_id, param_name, param_value):
        """Добавление или обновление параметра у пользователя"""
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id][param_name] = param_value
            self.save_users()
            return True
        return False

    def get_user(self, user_id):
        """Получение информации о пользователе"""
        return self.users.get(str(user_id), None)

    def get_user_by_username(self, username: str):
        """Поиск пользователя по Telegram username (@ник)"""
        for uid, data in self.users.items():
            if data.get("tg_username") == username.lstrip(
                "@"
            ):  # убираем @ если передали
                return {"user_id": uid, **data}
        return None

    def check_user_param_value(self, user_id, param_name, value):
        """
        Проверка значения параметра у пользователя.

        :param user_id: ID пользователя
        :param param_name: название параметра
        :param value: ожидаемое значение
        :return: True / False
        """
        user_id = str(user_id)
        if user_id in self.users and param_name in self.users[user_id]:
            return self.users[user_id][param_name] == value
        return False

    def list_users(self):
        """Вывод списка пользователей"""
        return self.users

    def check_user(self, user_id):
        """Проверка наличия пользователя"""
        return str(user_id) in self.users

    def get_mentors(self):
        """Возвращает список пользователей, у которых is_mentoring=True"""
        return [
            {"user_id": uid, **data}
            for uid, data in self.users.items()
            if data.get("is_mentoring") is True
        ]


usrsdb = UserDatabase()
