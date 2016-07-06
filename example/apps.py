from datetime import datetime
from edc_consent.apps import EdcConsentAppConfig as EdcConsentAppConfigParent
from django.apps.config import AppConfig


class ExampleAppConfig(AppConfig):
    name = 'example'
    institution = 'BHP'


class EdcConsentAppConfig(EdcConsentAppConfigParent):
    consent_type_setup = [
        {'app_label': 'example',
         'model_name': 'testconsentmodel',
         'start_datetime': datetime(2016, 5, 1, 0, 0, 0),
         'end_datetime': datetime(2017, 5, 1, 0, 0, 0),
         'version': '1'}]
