[![Build Status](https://travis-ci.org/botswana-harvard/edc-consent.svg?branch=develop)](https://travis-ci.org/botswana-harvard/edc-consent) [![Coverage Status](https://coveralls.io/repos/botswana-harvard/edc-consent/badge.svg?branch=develop&service=github)](https://coveralls.io/github/botswana-harvard/edc-consent?branch=develop)

# edc-consent

Add classes for the Informed Consent form and process.

## Installation
	
    pip install git+https://github.com/botswana-harvard/edc-consent@develop#egg=edc_consent
	
Declare your own AppConfig, `my_app.apps.py`, which will register your consent model, its version and period of validity. For now we just create a version 1 consent:

    from edc_base.utils import get_utcnow
    from edc_consent.apps import AppConfig as EdcConsentAppConfigParent
    from edc_consent.consent import Consent

    class EdcConsentAppConfig(EdcConsentAppConfigParent):

        consents = [
            Consent('edc_example.subjectconsent', version='1',
                    start=get_utcnow() - relativedelta(years=1),
                    end=get_utcnow() + relativedelta(years=1))
        ]

add to settings:

    INSTALLED_APPS = [
        ...
        'my_app.apps.EdcConsentAppConfig',
        ...
    ]



| _Below needs to be updated_ |

## Features

- base class for an informed consent document
- data for models that require consent cannot be add until the consent is added
- consents have a version number and validity period
- maximum number of consented subjects can be controlled.
- data collection is only allowed within the validity period of the consent per consented participant
- data for models that require consent are tagged with the consent version

## TODO

- link subject type to the consent model. e.g. maternal, infant, adult, etc.
- version at model field level (e.g. a new consent period adds additional questions to a form)
- allow a different subject's consent to cover for another, for example mother and infant. 

## Usage

First, it's a good idea to limit the number of consents created to match your enrollment targets. Do this by creating a mixin for the consent model class:

	from edc_quota.client.models import QuotaMixin, QuotaManager

	class ConsentQuotaMixin(QuotaMixin):
	
	    QUOTA_REACHED_MESSAGE = 'Maximum number of subjects has been reached or exceeded for {}. Got {} >= {}.'
	
	    class Meta:
	            abstract = True

Then declare the consent model:

	class MyConsent(ConsentQuotaMixin, BaseConsent):

    	quota = QuotaManager()

		class Meta:
			app_label = 'my_app'

Declare the ModelForm:

	class MyConsentForm(BaseConsentForm):

		class Meta:
			model = MyConsent
	

Now that you have a consent model class, identify and declare the models that will require this consent:

	class Questionnaire(RequiresConsentMixin, models.Model):

    	consent_model = MyConsent  # or tuple (app_label, model_name)

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
	
Notice above the first two class attributes, namely:

* consent_model: this is the consent model class that was declared above;
* report_datetime: a required field used to lookup the correct consent version from ConsentType and to find, together with `subject_identifier`,  a valid instance of `MyConsent`;

Also note the property `subject_identifier`. 

* subject_identifier: a required property that knows how to find the `subject_identifier` for the instance of `Questionnaire`.  

Once all is declared you need to:

* define the consent version and validity period for the consent version in `ConsentType`;
* add a Quota for the consent model.

As subjects are identified:

* add a consent
* add the models (e.g. `Questionnaire`)

If a consent version cannot be found given the consent model class and report_datetime a `ConsentTypeError` is raised.

If a consent for this subject_identifier cannot be found that matches the `ConsentType` a `NotConsentedError` is raised.

## Specimen Consent
A participant may consent to the study but not agree to have specimens stored long term. A specimen consent is administered separately to clarify the participant\'s intention.

The specimen consent is declared using the base class `BaseSpecimenConsent`. This is an abridged version of `BaseConsent`. The specimen consent also uses the `RequiresConsentMixin` as it cannot stand alone as an ICF. The `RequiresConsentMixin` ensures the specimen consent is administered after the main study ICF, in this case `MyStudyConsent`.

A specimen consent is declared in your app like this: 

        class SpecimenConsent(BaseSpecimenConsent, SampleCollectionFieldsMixin, RequiresConsentMixin,
                              VulnerabilityFieldsMixin, AppointmentMixin, BaseUuidModel):

        consent_model = MyStudyConsent

        registered_subject = models.OneToOneField(RegisteredSubject, null=True)

        objects = models.Manager()

        history = AuditTrail()

        class Meta:
            app_label = 'my_app'
            verbose_name = 'Specimen Consent'
 

## Validators

The `ConsentAgeValidator` validates the date of birth to within a given age range, for example:

	from edc_consent.validtors import ConsentAgeValidator
	
	class MyConsent(ConsentQuotaMixin, BaseConsent):

		dob = models.DateField(
	        validators=[ConsentAgeValidator(16, 64)])

    	quota = QuotaManager()

		class Meta:
			app_label = 'my_app'

The `PersonalFieldsMixin` includes a date of birth field and you can set the age bounds like this:

	from edc_consent.validtors import ConsentAgeValidator
	from edc_consent.models.fields import PersonalFieldsMixin
	
	class MyConsent(ConsentQuotaMixin, PersonalFieldsMixin, BaseConsent):
	
    	quota = QuotaManager()

        MIN_AGE_OF_CONSENT = 18
        MAX_AGE_OF_CONSENT = 64

		class Meta:
			app_label = 'my_app'


## Common senarios

### Tracking the consent version with collected data

All model data is tagged with the consent version identified in `ConsentType` for the consent model class and report_datetime.

### Reconsenting consented subjects when the consent changes

The consent model is unique on subject_identifier, identity and version. If a new consent version is added to `ConsentType`, a new consent will be required for each subject as data is reported within the validity period of the new consent.

Some care must be taken to ensure that the consent model is queried with an understanding of the unique constraint. 

### Linking the consent version to added or removed model fields on models that require consent

TODO

### Infants use mother's consent

TODO

By adding the property `consenting_subject_identifier` to the consent


## Other TODO

* `Timepoint` model update in `save` method of models requiring consent
* handle added or removed model fields (questions) because of consent version change
* review verification actions
* management command to update version on models that require consent (if edc_consent added after instances were created)
* handle re-consenting issues, for example, if original consent was restricted by age (16-64) but the re-consent is not. May need to open upper bound.



 

