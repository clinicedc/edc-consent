from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "consent_app"
    verbose_name = "Edc Consent test app"
    include_in_administration_section = False
