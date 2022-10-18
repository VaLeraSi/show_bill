from datetime import date

from simba_framework.templator import render
from patterns.сreational_patterns import Engine, Logger, MapperRegistry
from patterns.structural_patterns import AppRoute, Debug
from patterns.behavioral_patterns import EmailNotifier, SmsNotifier, \
    ListView, CreateView, BaseSerializer, ConsoleWriter
from patterns.architectural_system_pattern_unit_of_work import UnitOfWork

site = Engine()
logger = Logger('main', ConsoleWriter())
email_notifier = EmailNotifier()
sms_notifier = SmsNotifier()
UnitOfWork.new_current()
UnitOfWork.get_current().set_mapper_registry(MapperRegistry)

routes = {}


@AppRoute(routes=routes, url='/')
class Index:
    @Debug(name='Index')
    def __call__(self, request):
        return '200 OK', render('index.html')


# контроллер - музыкальных объявлений
@AppRoute(routes=routes, url='/music/')
class Music:
    @Debug(name='Music')
    def __call__(self, request):
        return '200 OK', render('music.html', date=date.today())


# контроллер - афиша кино
@AppRoute(routes=routes, url='/films/')
class Films:
    @Debug(name='Films')
    def __call__(self, request):
        return '200 OK', render('films.html', date=date.today())


# контроллер - театральная афиша
@AppRoute(routes=routes, url='/theatre/')
class Theatre:
    @Debug(name='Theatre')
    def __call__(self, request):
        return '200 OK', render('theatre.html', date=date.today())


# контроллер 404
class NotFound404:
    @Debug(name='NotFound404')
    def __call__(self, request):
        return '404 WHAT', '404 PAGE Not Found'


# контроллер - контакты
@AppRoute(routes=routes, url='/contacts/')
class Contacts:
    @Debug(name='Contacts')
    def __call__(self, request):
        return '200 OK', 'contacts'


@AppRoute(routes=routes, url='/posters/')
class Posters:
    @Debug(name='Posters')
    def __call__(self, request):
        return '200 OK', render('posters.html', objects_list=site.categories)


# контроллер - список объявлений
@AppRoute(routes=routes, url='/poster-list/')
class PosterList:
    def __call__(self, request):
        logger.log('Список объявлений')
        try:
            category = site.find_category_by_id(
                int(request['request_params']['id']))
            return '200 OK', render('poster_list.html',
                                    objects_list=category.posters,
                                    name=category.name, id=category.id)
        except KeyError:
            return '200 OK', 'No posters have been added yet'


# контроллер - создать объявление
@AppRoute(routes=routes, url='/create-posters/')
class CreatePoster:
    category_id = -1

    def __call__(self, request):
        if request['method'] == 'POST':
            # метод пост
            data = request['data']

            name = data['name']
            name = site.decode_value(name)

            category = None
            if self.category_id != -1:
                category = site.find_category_by_id(int(self.category_id))

                poster = site.create_poster('films', name, category)

                poster.observers.append(email_notifier)
                poster.observers.append(sms_notifier)

                site.posters.append(poster)

            return '200 OK', render('poster_list.html',
                                    objects_list=category.posters,
                                    name=category.name,
                                    id=category.id)

        else:
            try:
                self.category_id = int(request['request_params']['id'])
                category = site.find_category_by_id(int(self.category_id))

                return '200 OK', render('create_posters.html',
                                        name=category.name,
                                        id=category.id)
            except KeyError:
                return '200 OK', 'No categories have been added yet'


# контроллер - создать объявление
@AppRoute(routes=routes, url='/create-category/')
class CreateCategory:
    def __call__(self, request):

        if request['method'] == 'POST':
            # метод пост

            data = request['data']

            name = data['name']
            name = site.decode_value(name)

            category_id = data.get('category_id')

            category = None
            if category_id:
                category = site.find_category_by_id(int(category_id))

            new_category = site.create_category(name, category)

            site.categories.append(new_category)

            return '200 OK', render('posters.html', objects_list=site.categories)
        else:
            categories = site.categories
            return '200 OK', render('create_category.html',
                                    categories=categories)


# контроллер - список категорий
@AppRoute(routes=routes, url='/category-list/')
class CategoryList:
    def __call__(self, request):
        logger.log('Список категорий')
        return '200 OK', render('category_list.html',
                                objects_list=site.categories)


# контроллер - копировать объявление
@AppRoute(routes=routes, url='/copy-poster/')
class CopyPoster:
    def __call__(self, request):
        request_params = request['request_params']

        try:
            name = request_params['name']

            old_poster = site.get_poster(name)
            if old_poster:
                new_name = f'copy_{name}'
                new_poster = old_poster.clone()
                new_poster.name = new_name
                site.posters.append(new_poster)

            return '200 OK', render('poster_list.html',
                                    objects_list=site.posters,
                                    name=new_poster.category.name)
        except KeyError:
            return '200 OK', 'No courses have been added yet'


@AppRoute(routes=routes, url='/member-list/')
class MemberListView(ListView):
    queryset = site.persons_of_interest
    template_name = 'member_list.html'

    def get_queryset(self):
        mapper = MapperRegistry.get_current_mapper('person_of_interest')
        return mapper.all()


@AppRoute(routes=routes, url='/create-member/')
class MemberCreateView(CreateView):
    template_name = 'create_member.html'

    def create_obj(self, data: dict):
        name = data['name']
        name = site.decode_value(name)
        new_obj = site.create_user('person_of_interest', name)
        site.persons_of_interest.append(new_obj)
        new_obj.mark_new()
        UnitOfWork.get_current().commit()


@AppRoute(routes=routes, url='/add-member/')
class AddMemberByEventCreateView(CreateView):
    template_name = 'add_member.html'

    def get_context_data(self):
        context = super().get_context_data()
        context['posters'] = site.posters
        context['persons_of_interest'] = site.persons_of_interest
        return context

    def create_obj(self, data: dict):
        posters_name = data['poster_name']
        posters_name = site.decode_value(posters_name)
        poster = site.get_poster(posters_name)
        person_name = data['person_name']
        person_name = site.decode_value(person_name)
        person = site.get_person(person_name)
        poster.add_person(person)


@AppRoute(routes=routes, url='/api/')
class PosterApi:
    @Debug(name='PosterApi')
    def __call__(self, request):
        return '200 OK', BaseSerializer(site.posters).save()
