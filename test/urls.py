from django.urls import path
from django.http import HttpResponse


def view(request):
    return HttpResponse()


urlpatterns = [
    path('', view),
]
