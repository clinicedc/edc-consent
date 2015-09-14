[![Build Status](https://travis-ci.org/botswana-harvard/edc-consent.svg?branch=develop)](https://travis-ci.org/botswana-harvard/edc-consent)

# edc-consent
Add base classes for the Informed Consent form and process.

## Installation

	pip install edc-consent
	
Add to settings:

	MIN_AGE_OF_CONSENT = 16
	MAX_AGE_OF_CONSENT = 64
	AGE_IS_ADULT = 18
	GENDER_OF_CONSENT = ['M', 'F']	
	
## Features

- base class for an informed consent document
- data for models that require consent cannot be add until the consent is added
- consents have a version number and validity period
- maximum number of consented subjects can be controlled.
- data collection is only allowed within the validity period of the consent per consented participant
- data for models that require consent are tagged with the consent version

TODO
- link subject type to the consent model. e.g. maternal, infant, adult, etc.
- version at model field level (e.g. a new consent period adds additional questions to a form)
- allow a different subject's consent to cover for another, for example mother and infant. 

## Usage

First, it's a good idea to limit the number of to match your enrollment targets. Do this by creating a mixin for the consent model class:

	class ConsentQuotaMixin(QuotaMixin):
	
	    QUOTA_REACHED_MESSAGE = 'Maximum number of subjects has been reached or exceeded for {}. Got {} >= {}.'
	
	    class Meta:
	            abstract = True

Then declare the consent model:

	class MyConsent(ConsentQuotaMixin, BaseConsent):

		class Meta:
			app_label = 'my_app'

Now that you have a consent model class, identify and declare the models that will require this consent:

	class Questionnaire(RequiresConsentMixin, models.Model):

    	CONSENT_MODEL = MyConsent

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

* CONSENT_MODEL: this is the consent model class that was declared above;
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

If a consent for this subject_identifier cannot be found that matches the `ConsentType` and `NotConsentedError` is raised.


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