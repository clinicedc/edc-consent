|pypi| |actions| |codecov| |downloads|

edc-consent
-----------

Add classes for the Informed Consent form and process.

Installation
============

Declare the consent model:

.. code-block:: python

    class SubjectConsent(
        ConsentModelMixin,
        SiteModelMixin,
        UpdatesOrCreatesRegistrationModelMixin,
        NonUniqueSubjectIdentifierModelMixin,
        IdentityFieldsMixin,
        PersonalFieldsMixin,
        SampleCollectionFieldsMixin,
        ReviewFieldsMixin,
        VulnerabilityFieldsMixin,
        SearchSlugModelMixin,
        BaseUuidModel,
    ):

        """A model completed by the user that captures the ICF."""

        subject_identifier_cls = SubjectIdentifier

        subject_screening_model = "effect_screening.subjectscreening"

        objects = SubjectConsentManager()
        on_site = CurrentSiteManager()
        consent = ConsentManager()
        history = HistoricalRecords()

        class Meta(ConsentModelMixin.Meta, BaseUuidModel.Meta):
            pass

Declare at least one ``ConsentDefinition`` that references your consent model.

``ConsentDefinitions`` are declared in the root of your app in module ``consents.py``. A typical declaration looks something like this:

.. code-block:: python

    from datetime import datetime
    from zoneifo import ZoneInfo

    from edc_consent.consent_definition import ConsentDefinition
    from edc_consent.site_consents import site_consents
    from edc_constants.constants import MALE, FEMALE

    consent_v1 = ConsentDefinition(
        'edc_example.subjectconsent',
        version='1',
        start=datetime(2013, 10, 15, tzinfo=ZoneInfo("UTC")),
        end=datetime(2016, 10, 15, 23, 59, 999999, tzinfo=ZoneInfo("UTC")),
        age_min=16,
        age_is_adult=18,
        age_max=64,
        gender=[MALE, FEMALE])

    site_consents.register(consent_v1)


add to settings:

.. code-block:: bash

    INSTALLED_APPS = [
        ...
        'edc_consent.apps.AppConfig',
        ...
    ]

On bootup ``site_consents`` will ``autodiscover`` the ``consents.py`` and register the ``ConsentDefinition``.

Now create an instance of the ``SubjectConsent`` model, ``subject_consent``. When the instance is saved, the model will find the ``ConsentDefinition`` with a validity period that includes ``subject_consent.consent_datetime`` and update ``subject_consent.version`` with the value of ``consent_definition.version``.
In this case, for ``consent_datetime`` equal to ``datetime(2013, 10, 16, tzinfo=ZoneInfo("UTC"))``, the model will find ``consent_v1``.
If the ``consent_datetime`` is outside of the date boundary, for example datetime(2017, 1, 1, tzinfo=ZoneInfo("UTC")), the model will not find a
``ConsentDefinition`` and an exception will be raised (``ConsentDefinitionNotFound``).

Add a second ``ConsentDefinition`` to ``your consents.py`` for version 2:

.. code-block:: python

    consent_v1 = ConsentDefinition(...)

    consent_v2 = ConsentDefinition(
        'edc_example.subjectconsent',
        version='2',
        start=datetime(2016, 10, 16, 0,0,0, tzinfo=ZoneInfo("UTC")),
        end=datetime(2020, 10, 15, 23, 59, 999999, tzinfo=ZoneInfo("UTC")),
        age_min=16,
        age_is_adult=18,
        age_max=64,
        gender=[MALE, FEMALE])

    site_consents.register(consent_v1)
    site_consents.register(consent_v2)


Now resave the instance from above with ``consent_datetime = datetime(2017, 1, 1, tzinfo=ZoneInfo("UTC"))``. The model will find
``consent_v2`` and update ``subject_consent.version = consent_v2.version`` which in this case is "2".

``edc_consent`` is coupled with ``edc_visit_schedule``. In fact, a data collection schedule is declared with one or more ``ConsentDefinitions``. CRFs and Requisitions listed in a schedule may only be submitted if the subject has consented.

.. code-block:: python

    schedule = Schedule(
        name=SCHEDULE,
        verbose_name="Day 1 to Month 6 Follow-up",
        onschedule_model="effect_prn.onschedule",
        offschedule_model="effect_prn.endofstudy",
        consent_definitions=[consent_v1, consent_v2],
    )

When a CRF is saved, the CRF model will check the ``schedule`` to find the ``ConsentDefinition`` with a validity period that contains the ``crf.report_datetime``. Using the located ``ConsentDefinitions``, the CRF model will confirm the subject has a saved ``subject_consent`` with this ``consent_definition.version``.

When there is more than one ``ConsentDefinition`` but still just one ``SubjectConsent`` model, declaring proxy models
provides some clarity and allows the ``ModelForm`` and ``ModelAdmin`` classes to be customized.

.. code-block:: python

    class SubjectConsentV1(SubjectConsent):

        class Meta:
            proxy = True
            verbose_name = "Consent V1"
            verbose_name_plural = "Consent V1"


    class SubjectConsentV2(SubjectConsent):

        class Meta:
            proxy = True
            verbose_name = "Consent V2"
            verbose_name_plural = "Consent V2"


.. code-block:: python

    consent_v1 = ConsentDefinition(
        'edc_example.subjectconsentv1',
        version='1', ...)

    consent_v2 = ConsentDefinition(
        'edc_example.subjectconsentv2',
        version='2', ...)

    site_consents.register(consent_v1)
    site_consents.register(consent_v2)

Now each model can use a custom ``ModelAdmin`` class.

The ConsentDefinitions above assume that consent version 1 is completed for a subject
consenting on or before 2016/10/15 and version 2 for those consenting after 2016/10/15.

Sometimes when version 2 is introduced, those subjects who consented for version 1 need
to update their version 1 consent to version 2. For example, a question may have been added
in version 2 to allow a subject to opt-out of having their specimens put into longterm
storage. The subjects who are already consented under version 1 need to indicate their
preference as well by submitting a version 2 consent. (To make things simple, we would
programatically carry-over and validate duplicate data from the subject's version 1 consent.)

To allow this, we would add ``update_versions`` to the version 2 ``ConsentDefinition``.

.. code-block:: python

    consent_v1 = ConsentDefinition(
        'edc_example.subjectconsentv1',
        version='1', ...)

    consent_v2 = ConsentDefinition(
        'edc_example.subjectconsentv2',
        version='2',
        update_versions=[UpdateVersion(consent_v1.version, consent_v1.end)],

    site_consents.register(consent_v1)
    site_consents.register(consent_v2)

As the trial continues past 2016/10/15, there will three categories of subjects:

* Subjects who completed version 1 only
* Subjects who completed version 1 and version 2
* Subjects who completed version 2 only

If the report date is after 2016/10/15, data entry for "Subjects who completed version 1 only"
will be blocked until the version 2 consent is submitted.





Features
========

* base class for an informed consent document
* data for models that require consent cannot be add until the consent is added
* consents have a version number and validity period
* maximum number of consented subjects can be controlled.
* data collection is only allowed within the validity period of the consent per consented participant
* data for models that require consent are tagged with the consent version

TODO
====

- link subject type to the consent model. e.g. maternal, infant, adult, etc.
- version at model field level (e.g. a new consent period adds additional questions to a form)
- allow a different subject's consent to cover for another, for example mother and infant.

Usage
=====



Declare the ModelForm:

.. code-block:: python

    class SubjectConsentForm(BaseConsentForm):

        class Meta:
            model = SubjectConsent


Now that you have a consent model class, declare the models that will require this consent:

.. code-block:: python

    class Questionnaire(RequiresConsentMixin, models.Model):

        report_datetime = models.DateTimeField(default=timezone.now)

        question1 = models.CharField(max_length=10)

        question2 = models.CharField(max_length=10)

        question3 = models.CharField(max_length=10)

    @property
    def subject_identifier(self):
        """Returns the subject identifier from ..."""
        return subject_identifier

    class Meta:
        app_label = 'my_app'
        verbose_name = 'My Questionnaire'


* report_datetime: a required field used to lookup the correct ``ConsentDefinition`` and to find, together with ``subject_identifier``,  a valid instance of ``SubjectConsent``;
* subject_identifier: a required field or may be a property that knows how to find the ``subject_identifier`` for the instance of ``Questionnaire``.

Once all is declared you need to:

* define the consent version and validity period for the consent version in ``ConsentDefinition``;
* add a Quota for the consent model.

As subjects are identified:

* add a consent
* add the models (e.g. ``Questionnaire``)

If a consent version cannot be found given the consent model class and report_datetime a ``ConsentDefinitionError`` is raised.

If a consent for this subject_identifier cannot be found that matches the ``ConsentDefinition`` a ``NotConsentedError`` is raised.

Specimen Consent
================

A participant may consent to the study but not agree to have specimens stored long term. A specimen consent is administered separately to clarify the participant\'s intention.

The specimen consent is declared using the base class ``BaseSpecimenConsent``. This is an abridged version of ``BaseConsent``. The specimen consent also uses the ``RequiresConsentMixin`` as it cannot stand alone as an ICF. The ``RequiresConsentMixin`` ensures the specimen consent is administered after the main study ICF, in this case ``MyStudyConsent``.

A specimen consent is declared in your app like this:

.. code-block:: python

        class SpecimenConsent(
            BaseSpecimenConsent, SampleCollectionFieldsMixin, RequiresConsentMixin,
            VulnerabilityFieldsMixin, AppointmentMixin, BaseUuidModel
        ):

            consent_model = MyStudyConsent

            registered_subject = models.OneToOneField(RegisteredSubject, null=True)

            objects = models.Manager()

            history = AuditTrail()

        class Meta:
            app_label = 'my_app'
            verbose_name = 'Specimen Consent'


Validators
==========

The ``ConsentAgeValidator`` validates the date of birth to within a given age range, for example:

.. code-block:: python

    from edc_consent.validtors import ConsentAgeValidator

    class MyConsent(ConsentQuotaMixin, BaseConsent):

        dob = models.DateField(
            validators=[ConsentAgeValidator(16, 64)])

        quota = QuotaManager()

        class Meta:
            app_label = 'my_app'

The ``PersonalFieldsMixin`` includes a date of birth field and you can set the age bounds like this:

.. code-block:: python

    from edc_consent.validtors import ConsentAgeValidator
    from edc_consent.models.fields import PersonalFieldsMixin

    class MyConsent(ConsentQuotaMixin, PersonalFieldsMixin, BaseConsent):

        quota = QuotaManager()

        MIN_AGE_OF_CONSENT = 18
        MAX_AGE_OF_CONSENT = 64

        class Meta:
            app_label = 'my_app'


Common senarios
===============

Tracking the consent version with collected data
++++++++++++++++++++++++++++++++++++++++++++++++

All model data is tagged with the consent version identified in ``ConsentDefinition`` for the consent model class and report_datetime.

Reconsenting consented subjects when the consent changes
++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The consent model is unique on subject_identifier, identity and version. If a new consent version is added to ``ConsentDefinition``, a new consent will be required for each subject as data is reported within the validity period of the new consent.

Some care must be taken to ensure that the consent model is queried with an understanding of the unique constraint.


Linking the consent version to added or removed model fields on models that require consent
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

TODO

Infants use mother's consent
++++++++++++++++++++++++++++

TODO

By adding the property ``consenting_subject_identifier`` to the consent


Patient names
=============
If patient names need to be removed from the data collection, there are a few helper
attributes and methods to consider.

``settings.EDC_CONSENT_REMOVE_PATIENT_NAMES_FROM_COUNTRIES: list[str]``

If given a list of country names, name fields will be removed from any admin.fieldset.

See also edc_sites.all_sites

``ConsentModelAdminMixin.get_fieldsets``

.. code-block:: python

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        for country in get_remove_patient_names_from_countries():
            site = getattr(request, "site", None)
            if site and site.id in [s.site_id for s in self.all_sites.get(country)]:
                return self.fieldsets_without_names(fieldsets)
        return fieldsets

This method could be added to any ModeLadmin with names.



using


Other TODO
==========

* ``Timepoint`` model update in ``save`` method of models requiring consent
* handle added or removed model fields (questions) because of consent version change
* review verification actions
* management command to update version on models that require consent (if edc_consent added after instances were created)
* handle re-consenting issues, for example, if original consent was restricted by age (16-64) but the re-consent is not. May need to open upper bound.



.. |pypi| image:: https://img.shields.io/pypi/v/edc-consent.svg
    :target: https://pypi.python.org/pypi/edc-consent

.. |actions| image:: https://github.com/clinicedc/edc-consent/actions/workflows/build.yml/badge.svg
  :target: https://github.com/clinicedc/edc-consent/actions/workflows/build.yml

.. |codecov| image:: https://codecov.io/gh/clinicedc/edc-consent/branch/develop/graph/badge.svg
  :target: https://codecov.io/gh/clinicedc/edc-consent

.. |downloads| image:: https://pepy.tech/badge/edc-consent
   :target: https://pepy.tech/project/edc-consent
