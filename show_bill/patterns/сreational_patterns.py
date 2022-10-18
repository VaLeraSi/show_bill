from copy import deepcopy
from sqlite3 import connect
from quopri import decodestring
from patterns.behavioral_patterns import FileWriter, Subject
from patterns.architectural_system_pattern_unit_of_work import DomainObject


# абстрактный пользователь
class User:
    def __init__(self, name):
        self.name = name


# администратор
class Administrator(User):
    pass


# пользователи, просматривающие объявления
class Person_of_interest(User, DomainObject):

    def __init__(self, name):
        self.posters = []
        super().__init__(name)


class UserFactory:
    types = {
        'person_of_interest': Person_of_interest,
        'administrator': Administrator
    }

    # порождающий паттерн Фабричный метод
    @classmethod
    def create(cls, type_, name):
        return cls.types[type_](name)


# порождающий паттерн Прототип
class PosterPrototype:
    # прототип объявления

    def clone(self):
        return deepcopy(self)


class Poster(PosterPrototype, Subject):

    def __init__(self, name, category):
        self.name = name
        self.category = category
        self.category.posters.append(self)
        self.persons_of_interest = []
        super().__init__()

    def __getitem__(self, item):
        return self.persons_of_interest[item]

    def add_person(self, person_of_interest: Person_of_interest):
        self.persons_of_interest.append(person_of_interest)
        person_of_interest.posters.append(self)
        self.notify()


# музыкальная афиша
class Music(Poster):
    pass


# афиша кино
class Films(Poster):
    pass


# театральная афиша
class Theatre(Poster):
    pass


# категория
class Category:
    auto_id = 0

    def __init__(self, name, category):
        self.id = Category.auto_id
        Category.auto_id += 1
        self.name = name
        self.category = category
        self.posters = []

    def poster_count(self):
        result = len(self.posters)
        if self.category:
            result += self.name.poster_count()
        return result


class PosterFactory:
    types = {
        'music': Music,
        'films': Films,
        'theatre': Theatre,
    }

    # порождающий паттерн Фабричный метод
    @classmethod
    def create(cls, type_, name, category):
        return cls.types[type_](name, category)


# основной интерфейс проекта
class Engine:
    def __init__(self):
        self.administrators = []
        self.persons_of_interest = []
        self.categories = []
        self.posters = []

    @staticmethod
    def create_user(type_, name):
        return UserFactory.create(type_, name)

    @staticmethod
    def create_category(name, category=None):
        return Category(name, category)

    def find_category_by_id(self, id):
        for item in self.categories:
            print('item', item.id)
            if item.id == id:
                return item
        raise Exception(f'Нет категории с id = {id}')

    @staticmethod
    def create_poster(type_, name, category):
        return PosterFactory.create(type_, name, category)

    def get_poster(self, name):
        for item in self.posters:
            if item.name == name:
                return item
        return None

    def get_person(self, name) -> Person_of_interest:
        for item in self.persons_of_interest:
            if item.name == name:
                return item

    @staticmethod
    def decode_value(val):
        val_b = bytes(val.replace('%', '=').replace("+", " "), 'UTF-8')
        val_decode_str = decodestring(val_b)
        return val_decode_str.decode('UTF-8')


# порождающий паттерн Синглтон
class SingletonByName(type):

    def __init__(cls, name, bases, attrs, **kwargs):
        super().__init__(name, bases, attrs)
        cls.__instance = {}

    def __call__(cls, *args, **kwargs):
        if args:
            name = args[0]
        if kwargs:
            name = kwargs['name']

        if name in cls.__instance:
            return cls.__instance[name]
        else:
            cls.__instance[name] = super().__call__(*args, **kwargs)
            return cls.__instance[name]


class Logger(metaclass=SingletonByName):

    def __init__(self, name, writer=FileWriter()):
        self.name = name
        self.writer = writer

    def log(self, text):
        text = f'log---> {text}'
        self.writer.write(text)


class PersonMapper:

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self.tablename = 'person_of_interest'

    def all(self):
        statement = f'SELECT * from {self.tablename}'
        self.cursor.execute(statement)
        result = []
        for item in self.cursor.fetchall():
            id, name = item
            person_of_interest = Person_of_interest(name)
            person_of_interest.id = id
            result.append(person_of_interest)
        return result

    def find_by_id(self, id):
        statement = f"SELECT id, name FROM {self.tablename} WHERE id=?"
        self.cursor.execute(statement, (id,))
        result = self.cursor.fetchone()
        if result:
            return Person_of_interest(*result)
        else:
            raise RecordNotFoundException(f'record with id={id} not found')

    def insert(self, obj):
        statement = f"INSERT INTO {self.tablename} (name) VALUES (?)"
        self.cursor.execute(statement, (obj.name,))
        try:
            self.connection.commit()
        except Exception as e:
            raise DbCommitException(e.args)

    def update(self, obj):
        statement = f"UPDATE {self.tablename} SET name=? WHERE id=?"

        self.cursor.execute(statement, (obj.name, obj.id))
        try:
            self.connection.commit()
        except Exception as e:
            raise DbUpdateException(e.args)

    def delete(self, obj):
        statement = f"DELETE FROM {self.tablename} WHERE id=?"
        self.cursor.execute(statement, (obj.id,))
        try:
            self.connection.commit()
        except Exception as e:
            raise DbDeleteException(e.args)


connection = connect('patterns.sqlite')


# архитектурный системный паттерн - Data Mapper
class MapperRegistry:
    mappers = {
        'person_of_interest': PersonMapper,
        # 'category': CategoryMapper
    }

    @staticmethod
    def get_mapper(obj):
        if isinstance(obj, Person_of_interest):
            return PersonMapper(connection)

    @staticmethod
    def get_current_mapper(name):
        return MapperRegistry.mappers[name](connection)


class DbCommitException(Exception):
    def __init__(self, message):
        super().__init__(f'Db commit error: {message}')


class DbUpdateException(Exception):
    def __init__(self, message):
        super().__init__(f'Db update error: {message}')


class DbDeleteException(Exception):
    def __init__(self, message):
        super().__init__(f'Db delete error: {message}')


class RecordNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(f'Record not found: {message}')
