from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.test import TestCase, override_settings
from edc_protocol.research_protocol_config import ResearchProtocolConfig
from edc_registration.models import RegisteredSubject
from edc_utils import get_utcnow
from edc_visit_schedule.site_visit_schedules import site_visit_schedules
from model_bakery import baker

from edc_consent.exceptions import (
    ConsentDefinitionDoesNotExist,
    ConsentDefinitionError,
    ConsentVersionSequenceError,
    NotConsentedError,
    SiteConsentError,
)
from edc_consent.site_consents import site_consents

from ..consent_test_utils import consent_definition_factory
from ..models import CrfOne, SubjectVisit
from ..visit_schedules import get_visit_schedule


@override_settings(
    EDC_PROTOCOL_STUDY_OPEN_DATETIME=get_utcnow() - relativedelta(years=5),
    EDC_PROTOCOL_STUDY_CLOSE_DATETIME=get_utcnow() + relativedelta(years=1),
    EDC_AUTH_SKIP_SITE_AUTHS=True,
    EDC_AUTH_SKIP_AUTH_UPDATER=False,
)
class TestConsent(TestCase):
    def setUp(self):
        site_consents.registry = {}
        self.study_open_datetime = ResearchProtocolConfig().study_open_datetime
        self.study_close_datetime = ResearchProtocolConfig().study_close_datetime
        self.subject_identifier = "12345"
        super().setUp()

    def test_raises_error_if_no_consent(self):
        """Asserts SubjectConsent cannot create a new instance if
        no consents are defined.

        Note: site_consents.reset_registry called in setUp.
        """
        subject_identifier = self.subject_identifier
        self.assertRaises(
            SiteConsentError,
            baker.make_recipe,
            "edc_consent.subjectconsent",
            subject_identifier=subject_identifier,
            consent_datetime=self.study_open_datetime,
        )

    def test_raises_error_if_no_consent2(self):
        """Asserts a model using the RequiresConsentMixin cannot create
        a new instance if subject not consented.
        """
        consent_definition = consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_close_datetime,
        )
        visit_schedule = get_visit_schedule(consent_definition)
        schedule = visit_schedule.schedules.get("schedule1")
        site_visit_schedules._registry = {}
        site_visit_schedules.register(get_visit_schedule(consent_definition))
        RegisteredSubject.objects.create(subject_identifier=self.subject_identifier)
        self.assertRaises(
            NotConsentedError,
            SubjectVisit.objects.create,
            report_datetime=self.study_open_datetime,
            subject_identifier=self.subject_identifier,
            visit_schedule_name=visit_schedule.name,
            schedule_name=schedule.name,
        )

    def test_allows_create_if_consent(self):
        """Asserts can create a consent model instance if a valid
        consent.
        """
        consent_definition = consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_close_datetime,
        )
        visit_schedule = get_visit_schedule(consent_definition)
        schedule = visit_schedule.schedules.get("schedule1")
        site_visit_schedules._registry = {}
        site_visit_schedules.register(get_visit_schedule(consent_definition))
        subject_consent = baker.make_recipe(
            "edc_consent.subjectconsent",
            subject_identifier=self.subject_identifier,
            consent_datetime=self.study_open_datetime,
            dob=self.study_open_datetime - relativedelta(years=25),
        )
        subject_visit = SubjectVisit.objects.create(
            report_datetime=subject_consent.consent_datetime,
            subject_identifier=self.subject_identifier,
            visit_schedule_name=visit_schedule.name,
            schedule_name=schedule.name,
        )
        try:
            CrfOne.objects.create(
                subject_visit=subject_visit,
                subject_identifier=self.subject_identifier,
                report_datetime=self.study_open_datetime,
            )
        except NotConsentedError:
            self.fail("NotConsentedError unexpectedly raised")

    def test_cannot_create_consent_without_consent_by_datetime(self):
        consent_definition_factory(
            start=self.study_open_datetime + relativedelta(days=5),
            end=self.study_close_datetime,
            version="1",
        )
        self.assertRaises(
            ConsentDefinitionDoesNotExist,
            baker.make_recipe,
            "edc_consent.subjectconsent",
            dob=self.study_open_datetime - relativedelta(years=25),
            consent_datetime=self.study_open_datetime,
        )

    def test_consent_gets_version(self):
        consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_close_datetime,
            version="1.0",
        )
        consent = baker.make_recipe(
            "edc_consent.subjectconsent",
            consent_datetime=self.study_open_datetime,
            dob=self.study_open_datetime - relativedelta(years=25),
        )
        self.assertEqual(consent.version, "1.0")

    def test_model_gets_version(self):
        consent_definition = consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_close_datetime,
            version="1.0",
        )
        subject_consent = baker.make_recipe(
            "edc_consent.subjectconsent",
            subject_identifier=self.subject_identifier,
            consent_datetime=self.study_open_datetime,
            dob=self.study_open_datetime - relativedelta(years=25),
        )

        visit_schedule = get_visit_schedule(consent_definition)
        schedule = visit_schedule.schedules.get("schedule1")
        site_visit_schedules._registry = {}
        site_visit_schedules.register(get_visit_schedule(consent_definition))

        subject_visit = SubjectVisit.objects.create(
            report_datetime=subject_consent.consent_datetime,
            subject_identifier=self.subject_identifier,
            visit_schedule_name=visit_schedule.name,
            schedule_name=schedule.name,
        )

        crf_one = CrfOne.objects.create(
            subject_visit=subject_visit,
            subject_identifier=self.subject_identifier,
            report_datetime=subject_consent.consent_datetime,
        )
        self.assertEqual(crf_one.consent_version, "1.0")

    def test_model_consent_version_no_change(self):
        consent_definition = consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_close_datetime,
            version="1.2",
        )
        baker.make_recipe(
            "edc_consent.subjectconsent",
            subject_identifier=self.subject_identifier,
            consent_datetime=self.study_open_datetime,
            dob=self.study_open_datetime - relativedelta(years=25),
        )

        visit_schedule = get_visit_schedule(consent_definition)
        schedule = visit_schedule.schedules.get("schedule1")
        site_visit_schedules._registry = {}
        site_visit_schedules.register(get_visit_schedule(consent_definition))

        subject_visit = SubjectVisit.objects.create(
            subject_identifier=self.subject_identifier,
            visit_schedule_name=visit_schedule.name,
            schedule_name=schedule.name,
        )

        crf_one = CrfOne.objects.create(
            subject_visit=subject_visit,
            subject_identifier=self.subject_identifier,
            report_datetime=self.study_open_datetime,
        )
        self.assertEqual(crf_one.consent_version, "1.2")
        crf_one.save()
        self.assertEqual(crf_one.consent_version, "1.2")

    def test_model_consent_version_changes_with_report_datetime(self):
        consent_definition10 = consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        consent_definition11 = consent_definition_factory(
            start=self.study_open_datetime + timedelta(days=51),
            end=self.study_open_datetime + timedelta(days=100),
            version="1.1",
        )
        consent_datetime = self.study_open_datetime + timedelta(days=10)

        subject_consent = baker.make_recipe(
            "edc_consent.subjectconsent",
            subject_identifier=self.subject_identifier,
            consent_datetime=consent_datetime,
            dob=self.study_open_datetime - relativedelta(years=25),
        )

        self.assertEqual(subject_consent.version, "1.0")
        self.assertEqual(subject_consent.subject_identifier, self.subject_identifier)
        self.assertEqual(subject_consent.consent_datetime, consent_datetime)

        visit_schedule = get_visit_schedule([consent_definition10, consent_definition11])
        schedule = visit_schedule.schedules.get("schedule1")
        site_visit_schedules._registry = {}
        site_visit_schedules.register(visit_schedule)

        subject_visit = SubjectVisit.objects.create(
            report_datetime=consent_datetime,
            subject_identifier=self.subject_identifier,
            visit_schedule_name=visit_schedule.name,
            schedule_name=schedule.name,
        )

        crf_one = CrfOne.objects.create(
            subject_visit=subject_visit,
            subject_identifier=self.subject_identifier,
            report_datetime=consent_datetime,
        )
        self.assertEqual(crf_one.consent_version, "1.0")
        consent_datetime = self.study_open_datetime + timedelta(days=60)
        subject_consent = baker.make_recipe(
            "edc_consent.subjectconsent",
            subject_identifier=self.subject_identifier,
            consent_datetime=consent_datetime,
            dob=self.study_open_datetime - relativedelta(years=25),
        )
        crf_one.delete()
        crf_one.report_datetime = consent_datetime
        crf_one = CrfOne.objects.create(
            subject_visit=subject_visit,
            subject_identifier=self.subject_identifier,
            report_datetime=consent_datetime,
        )

        # Mcrf_one.save()
        self.assertEqual(crf_one.consent_version, "1.1")

    def test_consent_update_needs_previous_version(self):
        """Asserts that a consent type updates a previous consent."""
        consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        # specify updates version that does not exist, raises
        self.assertRaises(
            ConsentDefinitionError,
            consent_definition_factory,
            start=self.study_open_datetime + timedelta(days=51),
            end=self.study_open_datetime + timedelta(days=100),
            version="1.1",
            updates_versions=["1.2"],
        )
        # specify updates version that exists, ok
        consent_definition_factory(
            start=self.study_open_datetime + timedelta(days=51),
            end=self.study_open_datetime + timedelta(days=100),
            version="1.1",
            updates_versions=["1.0"],
        )

    def test_consent_model_needs_previous_version(self):
        """Asserts that a consent updates a previous consent but cannot
        be entered without an existing instance for the previous
        version."""
        consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        consent_definition_factory(
            start=self.study_open_datetime + timedelta(days=51),
            end=self.study_open_datetime + timedelta(days=100),
            version="1.1",
            updates_versions=["1.0"],
        )
        self.assertRaises(
            ConsentVersionSequenceError,
            baker.make_recipe,
            "edc_consent.subjectconsent",
            dob=self.study_open_datetime - relativedelta(years=25),
            consent_datetime=self.study_open_datetime + timedelta(days=60),
        )

    def test_consent_needs_previous_version2(self):
        """Asserts that a consent model updates its previous consent."""
        consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        consent_definition_factory(
            start=self.study_open_datetime + timedelta(days=51),
            end=self.study_open_datetime + timedelta(days=100),
            version="1.1",
            updates_versions=["1.0"],
        )
        subject_consent = baker.make_recipe(
            "edc_consent.subjectconsent",
            consent_datetime=self.study_open_datetime + timedelta(days=5),
            dob=self.study_open_datetime - relativedelta(years=25),
        )
        self.assertEqual(subject_consent.version, "1.0")
        subject_consent = baker.make_recipe(
            "edc_consent.subjectconsent",
            subject_identifier=subject_consent.subject_identifier,
            consent_datetime=self.study_open_datetime + timedelta(days=60),
            first_name=subject_consent.first_name,
            last_name=subject_consent.last_name,
            initials=subject_consent.initials,
            identity=subject_consent.identity,
            confirm_identity=subject_consent.identity,
            dob=subject_consent.dob,
        )
        self.assertEqual(subject_consent.version, "1.1")

    def test_consent_needs_previous_version3(self):
        """Asserts that a consent updates a previous consent raises
        if a version is skipped.
        """
        consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        consent_definition_factory(
            start=self.study_open_datetime + timedelta(days=51),
            end=self.study_open_datetime + timedelta(days=100),
            version="1.1",
            updates_versions=["1.0"],
        )
        consent_definition_factory(
            start=self.study_open_datetime + timedelta(days=101),
            end=self.study_open_datetime + timedelta(days=150),
            version="1.2",
            updates_versions=["1.1"],
        )
        subject_consent = baker.make_recipe(
            "edc_consent.subjectconsent",
            consent_datetime=self.study_open_datetime,
            dob=self.study_open_datetime - relativedelta(years=25),
        )
        self.assertEqual(subject_consent.version, "1.0")
        # use a consent datetime within verion 1.2, skipping 1.1, raises
        self.assertRaises(
            ConsentVersionSequenceError,
            baker.make_recipe,
            "edc_consent.subjectconsent",
            consent_datetime=self.study_open_datetime + timedelta(days=125),
            subject_identifier=subject_consent.subject_identifier,
            first_name=subject_consent.first_name,
            last_name=subject_consent.last_name,
            initials=subject_consent.initials,
            identity=subject_consent.identity,
            confirm_identity=subject_consent.identity,
            dob=subject_consent.dob,
        )

    def test_consent_periods_cannot_overlap(self):
        consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        self.assertRaises(
            ConsentDefinitionError,
            consent_definition_factory,
            start=self.study_open_datetime + timedelta(days=25),
            end=self.study_open_datetime + timedelta(days=100),
            version="1.1",
            updates_versions=["1.0"],
        )

    def test_consent_periods_cannot_overlap2(self):
        consent_definition_factory(
            model="edc_consent.subjectconsent",
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        self.assertRaises(
            ConsentDefinitionError,
            consent_definition_factory,
            model="edc_consent.subjectconsent",
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.1",
        )

    def test_consent_periods_can_overlap_if_different_model(self):
        consent_definition_factory(
            model="edc_consent.subjectconsent",
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        try:
            consent_definition_factory(
                model="edc_consent.subjectconsent2",
                start=self.study_open_datetime,
                end=self.study_open_datetime + timedelta(days=50),
                version="1.0",
            )
        except ConsentDefinitionError:
            self.fail("ConsentPeriodOverlapError unexpectedly raised")

    def test_consent_before_open(self):
        """Asserts cannot register a consent with a start date
        before the study open date.
        """
        self.assertRaises(
            ConsentDefinitionError,
            consent_definition_factory,
            start=self.study_open_datetime - relativedelta(days=1),
            end=self.study_close_datetime + relativedelta(days=1),
            version="1.0",
        )

    def test_consent_may_update_more_than_one_version(self):
        consent_definition_factory(
            start=self.study_open_datetime,
            end=self.study_open_datetime + timedelta(days=50),
            version="1.0",
        )
        consent_definition_factory(
            start=self.study_open_datetime + timedelta(days=51),
            end=self.study_open_datetime + timedelta(days=100),
            version="2.0",
        )
        consent_definition_factory(
            start=self.study_open_datetime + timedelta(days=101),
            end=self.study_open_datetime + timedelta(days=150),
            version="3.0",
            updates_versions=["1.0", "2.0"],
        )

    def test_consent_definition_naive_datetime_start(self):
        """Asserts cannot register a consent with a start date
        before the study open date.
        """
        d = self.study_open_datetime
        dte = datetime(d.year, d.month, d.day, 0, 0, 0, 0)
        self.assertRaises(
            ConsentDefinitionError,
            consent_definition_factory,
            start=dte,
            end=self.study_close_datetime + relativedelta(days=1),
            version="1.0",
        )

    def test_consent_definition_naive_datetime_end(self):
        """Asserts cannot register a consent with a start date
        before the study open date.
        """
        d = self.study_close_datetime
        dte = datetime(d.year, d.month, d.day, 0, 0, 0, 0)
        self.assertRaises(
            ConsentDefinitionError,
            consent_definition_factory,
            start=self.study_open_datetime,
            end=dte,
            version="1.0",
        )
