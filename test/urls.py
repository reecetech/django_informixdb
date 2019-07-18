from django.conf.urls import url
from django.http import HttpResponse


def view(request):
    return HttpResponse()


urlpatterns = [
    url('', view),
]
