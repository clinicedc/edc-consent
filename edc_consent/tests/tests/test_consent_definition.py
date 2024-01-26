from dateutil.relativedelta import relativedelta
from django.test import TestCase, override_settings
from edc_protocol import Protocol
from edc_utils import get_utcnow

from edc_consent.exceptions import SiteConsentError
from edc_consent.site_consents import site_consents

from ...consent_definition import ConsentDefinition


@override_settings(
    EDC_PROTOCOL_STUDY_OPEN_DATETIME=get_utcnow() - relativedelta(years=5),
    EDC_PROTOCOL_STUDY_CLOSE_DATETIME=get_utcnow() + relativedelta(years=1),
    EDC_AUTH_SKIP_SITE_AUTHS=True,
    EDC_AUTH_SKIP_AUTH_UPDATER=False,
)
class TestConsentModel(TestCase):
    def setUp(self):
        self.study_open_datetime = Protocol().study_open_datetime
        self.study_close_datetime = Protocol().study_close_datetime
        site_consents.registry = {}

    def default_options(self, **kwargs):
        options = dict(
            start=self.study_open_datetime,
            end=self.study_close_datetime,
            gender=["M", "F"],
            updates_versions=[],
            version="1",
            age_min=16,
            age_max=64,
            age_is_adult=18,
        )
        options.update(**kwargs)
        return options

    def test_ok(self):
        ConsentDefinition("edc_consent.subjectconsent", **self.default_options())

    def test_cdef_name(self):
        cdef1 = ConsentDefinition("edc_consent.subjectconsent", **self.default_options())
        self.assertEqual(cdef1.name, "edc_consent.subjectconsent-1")
        site_consents.register(cdef1)
        site_consents.get_consent_definition("edc_consent.subjectconsent")
        site_consents.get_consent_definition(model="edc_consent.subjectconsent")
        site_consents.get_consent_definition(version="1")

        # add country
        site_consents.registry = {}
        cdef1 = ConsentDefinition(
            "edc_consent.subjectconsentug", **self.default_options(country="uganda")
        )
        self.assertEqual(cdef1.name, "edc_consent.subjectconsentug-1")
        site_consents.register(cdef1)
        cdef2 = site_consents.get_consent_definition(country="uganda")
        self.assertEqual(cdef1, cdef2)

    def test_with_country(self):
        site_consents.registry = {}
        cdef1 = ConsentDefinition(
            "edc_consent.subjectconsent", country="uganda", **self.default_options()
        )
        site_consents.register(cdef1)
        cdef2 = site_consents.get_consent_definition(country="uganda")
        self.assertEqual(cdef1, cdef2)

    def test_with_country_raises_on_potential_duplicate(self):
        site_consents.registry = {}
        cdef1 = ConsentDefinition(
            "edc_consent.subjectconsent", country="uganda", **self.default_options()
        )
        cdef2 = ConsentDefinition(
            "edc_consent.subjectconsentug", country="uganda", **self.default_options()
        )
        site_consents.register(cdef1)
        site_consents.register(cdef2)
        self.assertRaises(
            SiteConsentError, site_consents.get_consent_definition, country="uganda"
        )