import pytest
from django.conf import settings


def pytest_configure():
    settings.configure(
        ROOT_URLCONF="test.urls",
        MIDDLEWARE=(),
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "test.datatypes",
        ),
        DATABASES={
            "default": {
                "ENGINE": "django_informixdb",
                "SERVER": "informix",
                "NAME": "adapter",
                "USER": "informix",
                "PASSWORD": "in4mix",
            },
        },
    )


@pytest.fixture(autouse=True)
def configure_caplog(caplog):
    caplog.set_level("INFO")
