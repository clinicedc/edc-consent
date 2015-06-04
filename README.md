[![Build Status](https://travis-ci.org/botswana-harvard/edc-consent.svg?branch=develop)](https://travis-ci.org/botswana-harvard/edc-consent)

# edc-consent
Add base classes for the Informed Consent form and process.

Installation
------------

	pip install edc-consent
	
Add to settings:

	MIN_AGE_OF_CONSENT = 16
	MAX_AGE_OF_CONSENT = 64
	AGE_IS_ADULT = 18
	GENDER_OF_CONSENT = ['M', 'F']
	
	# bypass unique constraint on the subject identifier in the consent model
	# see base_consent
	SUBJECT_IDENTIFIER_UNIQUE_ON_CONSENT = False  # default is True
	
	
Features
--------

- base class for an informed consent document
- models link to the consent cannot be used until the consent is complete
- consents are versioned
- data collection is only allowed within the validity period of the consent per consented participant
- link subject type to the consent model. e.g. maternal, infant, adult, etc.
- link max number of consented subjects to the consent.
 