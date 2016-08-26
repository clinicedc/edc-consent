from datetime import datetime
from edc_consent.apps import EdcConsentAppConfig as EdcConsentAppConfigParent
from django.apps.config import AppConfig


class AppConfig(AppConfig):
    name = 'example'


class EdcConsentAppConfig(EdcConsentAppConfigParent):
    consent_type_setup = [
        {'app_label': 'example',
         'model_name': 'testconsentmodel',
         'start_datetime': datetime(2013, 5, 1, 0, 0, 0),
         'end_datetime': datetime(2014, 5, 1, 0, 0, 0),
         'version': '1'},
        {'app_label': 'example',
         'model_name': 'testconsentmodel',
         'start_datetime': datetime(2014, 5, 2, 0, 0, 0),
         'end_datetime': datetime(2015, 5, 1, 0, 0, 0),
         'version': '2'},
        {'app_label': 'example',
         'model_name': 'testconsentmodel',
         'start_datetime': datetime(2015, 5, 2, 0, 0, 0),
         'end_datetime': datetime(2016, 12, 1, 0, 0, 0),
         'version': '3'},
    ]
