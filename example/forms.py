from example.models import TestConsentModel, TestConsentModelProxy
from edc_consent.forms.base_consent_form import BaseConsentForm


class ConsentForm(BaseConsentForm):

    class Meta:
        model = TestConsentModel
        fields = '__all__'


class ConsentModelProxyForm(BaseConsentForm):

    class Meta:
        model = TestConsentModelProxy
        fields = '__all__'
