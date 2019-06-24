from django.conf import settings


def pytest_configure():
    settings.configure(
        ROOT_URLCONF="tests.urls",
        MIDDLEWARE=(),
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "datatypes",
        ),
        DATABASES={
            "default": {
                "ENGINE": "django_informixdb",
                "SERVER": "dev",
                "NAME": "adapter",
                "USER": "informix",
                "PASSWORD": "in4mix",
            },
        },
    )
