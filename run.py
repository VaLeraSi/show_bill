from wsgiref.simple_server import make_server

from show_bill.simba_framework.main import Framework
from show_bill.urls import fronts
from show_bill.views import routes


application = Framework(routes, fronts)

with make_server('', 8080, application) as httpd:
    print("Запуск на порту 8080...")
    httpd.serve_forever()
