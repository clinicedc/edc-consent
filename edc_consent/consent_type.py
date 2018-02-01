from django.apps import apps as django_apps
from django.conf import settings
from edc_base.utils.convert import localize

from edc_consent.exceptions import ConsentTypeError


class AlreadyRegistered(Exception):
    pass


class ConsentType:

    def __init__(self, **kwargs):
        self.app_label = kwargs.get('app_label')
        self.model_name = kwargs.get('model_name')
        self.start_datetime = kwargs.get('start_datetime')
        self.end_datetime = kwargs.get('end_datetime')
        self.localize_dates()
        self.version = kwargs.get('version')
        self.updates_version = kwargs.get('updates_version', [])
        if self.updates_version:
            self.updates_version = ''.join([s for s in self.updates_version if s != ' '])
            self.updates_version = self.updates_version.split(',')

    def __str__(self):
        return 'Consent {}.{} version {}'.format(self.app_label, self.model_name, self.version)

    def slugify(self):
        return '{}-{}-{}'.format(self.app_label, self.model_name, self.version)

    def localize_dates(self):
        if settings.USE_TZ:
            if self.start_datetime:
                self.start_datetime = localize(self.start_datetime)
            if self.end_datetime:
                self.end_datetime = localize(self.end_datetime)

    @property
    def model_class(self):
        """Returns the consent model class."""
        return django_apps.get_model(self.app_label, self.model_name)

    def valid_for_consent_model(self, consent_model):
        return self.valid_for_model(self, model=consent_model)

    def valid_for_model(self, model=None, app_label=None, model_name=None):
        valid_for_consent_model = False
        if not model:
            model = django_apps.get_model(app_label, model_name)
        if model._meta.app_label == self.app_label and model._meta.model_name == self.model_name:
            valid_for_consent_model = True
        return valid_for_consent_model

    def valid_for_datetime(self, consent_datetime):
        valid_for_datetime = False
        if self.start_datetime <= consent_datetime <= self.end_datetime:
            valid_for_datetime = True
        return valid_for_datetime


class SiteConsentTypes:

    def __init__(self):
        self.registry = []
        self.check()

    def register(self, consent_type):
        for item in self.registry:
            if item.valid_for_model(consent_type.model_class):
                if (item.valid_for_datetime(consent_type.start_datetime) and
                        item.valid_for_datetime(consent_type.end_datetime)):
                    pass
#                     raise AlreadyRegistered('Consent type already registered. Got {}'.format(str(consent_type)))
        self.check_version(consent_type)
        self.check_updates_version(consent_type)
        self.check_consent_period(consent_type)
        self.registry.append(consent_type)

    def reset_registry(self):
        self.registry = []

    def all(self):
        return sorted(self.registry, key=lambda x: x.version, reverse=False)

    def check(self):
        for consent_type in self.registry:
            self.check_updates_version(consent_type)
            self.check_consent_period(consent_type)

    def get_by_model(self, model=None, app_label=None, model_name=None):
        consent_types = []
        for consent_type in self.registry:
            if consent_type.valid_for_model(model=model):
                consent_types.append(consent_type)
        return consent_types

    def get_by_version(self, version, app_label, model_name):
        consent_types = []
        for consent_type in self.registry:
            if (consent_type.version == version and
                    consent_type.valid_for_model(app_label=app_label, model_name=model_name)):
                consent_types.append(consent_type)
        return consent_types

    def get_all_by_version(self, version):
        consent_types = []
        for consent_type in self.registry:
            if consent_type.version == version:
                consent_types.append(consent_type)
        return consent_types

    def check_version(self, consent_type):
        if self.get_by_version(consent_type.version, consent_type.app_label, consent_type.model_name):
            raise AlreadyRegistered(
                'Consent version {1} for \'{2}.{3}\' is already registered'.format(
                    consent_type.updates_version, consent_type.version,
                    consent_type.app_label, consent_type.model_name))

    def check_updates_version(self, consent_type):
        for version in consent_type.updates_version:
            if not self.get_by_version(version, consent_type.app_label, consent_type.model_name):
                raise ConsentTypeError(
                    'Consent version {1} cannot be an update to version(s) \'{0}\'. '
                    'Version(s) \'{0}\' not found in \'{2}.{3}\''.format(
                        consent_type.updates_version, consent_type.version,
                        consent_type.app_label, consent_type.model_name))

    def check_consent_period(self, consent_type):
        registry = [ct for ct in self.registry if ct.slugify() != consent_type.slugify()]
        for ct in registry:
            if ct.app_label == consent_type.app_label and ct.model_name == consent_type.model_name:
                if (consent_type.start_datetime <= ct.start_datetime <= consent_type.end_datetime or
                        consent_type.start_datetime <= ct.end_datetime <= consent_type.end_datetime):
                    pass
#                     raise AlreadyRegistered(
#                         'Consent period for version {0} overlaps with version \'{1}\'. '
#                         'Got {2} to {3} overlaps with {4} to {5}.'.format(
#                             consent_type.updates_version, consent_type.version,
#                             ct.start_datetime.strftime('%Y-%m-%d'),
#                             ct.end_datetime.strftime('%Y-%m-%d'),
#                             consent_type.start_datetime.strftime('%Y-%m-%d'),
#                             consent_type.end_datetime.strftime('%Y-%m-%d')))

    def get_by_consent_datetime(self, consent_model, consent_datetime, version=None, exception_cls=None):
        return self.get_by_datetime(
            consent_model, consent_datetime, version=version, exception_cls=exception_cls)

    def get_by_report_datetime(self, consent_model, report_datetime, exception_cls=None):
        return self.get_by_datetime(
            consent_model, report_datetime, exception_cls=exception_cls)

    def get_by_datetime(self, model, my_datetime, version=None,  exception_cls=None):
        """Return consent type object valid for the datetime."""
        exception_cls = exception_cls or ConsentTypeError
        consent_types = []
        for consent_type in self.registry:
            if consent_type.valid_for_model(model) and consent_type.valid_for_datetime(my_datetime):
                consent_types.append(consent_type)
        if not consent_types:
            raise exception_cls(
                'Cannot find a version for consent \'{}\' using date \'{}\'. '
                'Check consent_type_setup in AppConfig.'.format(
                    model,
                    my_datetime.isoformat()))
        if len(consent_types) > 1:
            if version:
                for consent_type in consent_types:
                    if consent_type.version == version:
                        return consent_type
            else:
                raise exception_cls(
                    'More than one consent version found for date. '
                    'Check consent_type_setup in AppConfig for {}'.format(model))
        return consent_types[0]

    def get_by_datetime_lastest_version(self, model, my_datetime, exception_cls=None):
        """Return consent type object valid for the datetime."""
        exception_cls = exception_cls or ConsentTypeError
        consent_types = []
        versions = []
        for consent_type in self.registry:
            if consent_type.valid_for_model(model) and consent_type.valid_for_datetime(my_datetime):
                consent_types.append(consent_type)
        if not consent_types:
            raise exception_cls(
                'Cannot find a version for consent \'{}\' using date \'{}\'. '
                'Check consent_type_setup in AppConfig.'.format(
                    model,
                    my_datetime.isoformat()))
        if len(consent_types) > 1:
            for consent_type in consent_types:
                versions.append(consent_type.version)
            versions.sort()
        for consent_type in consent_types:
            if consent_type.version == versions[-1]:
                return consent_type
        return consent_types[0]

site_consent_types = SiteConsentTypes()