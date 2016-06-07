from datetime import datetime
from edc_consent.apps import EdcConsentAppConfig


class ConsentAppConfig(EdcConsentAppConfig):
    consent_type_setup = [
        {'app_label': 'bcpp_interview',
         'model_name': 'subjectconsent',
         'start_datetime': datetime(2016, 5, 1, 0, 0, 0),
         'end_datetime': datetime(2017, 5, 1, 0, 0, 0),
         'version': '1'},
        {'app_label': 'bcpp_interview',
         'model_name': 'nurseconsent',
         'start_datetime': datetime(2016, 5, 1, 0, 0, 0),
         'end_datetime': datetime(2017, 5, 1, 0, 0, 0),
         'version': '1'}]
