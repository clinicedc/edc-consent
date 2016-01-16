from django.db import models

from ..exceptions import NotConsentedError
from ..models import ConsentType


class RequiresConsentMixin(models.Model):

    consent_model = None

    consent_version = models.CharField(max_length=10, default='?', editable=False)

    def save(self, *args, **kwargs):
        self.consented_for_period_or_raise()
        super(RequiresConsentMixin, self).save(*args, **kwargs)

    def consented_for_period_or_raise(self, report_datetime=None, subject_identifier=None, exception_cls=None):
        exception_cls = exception_cls or NotConsentedError
        report_datetime = report_datetime or self.report_datetime
        consent_type = self.consent_type(report_datetime, exception_cls=exception_cls)
        self.consent_version = consent_type.version
        if not subject_identifier:
            try:
                subject_identifier = self.subject_identifier
            except AttributeError:
                subject_identifier = self.get_subject_identifier()
        try:
            self.consent_model.objects.get(
                subject_identifier=subject_identifier,
                version=self.consent_version)
        except self.consent_model.DoesNotExist:
            raise exception_cls(
                'Cannot find a consent \'{}\' for model \'{}\' using '
                'consent version \'{}\' and report date \'{}\'. '.format(
                    self.consent_model._meta.verbose_name,
                    self._meta.verbose_name,
                    self.consent_version,
                    report_datetime.isoformat()))

    def consent_type(self, report_datetime, exception_cls=None):
        """Returns the consent type that matches the report datetime and consent model."""
        return ConsentType.objects.get_by_report_datetime(
            self.consent_model, report_datetime, exception_cls=exception_cls)

    class Meta:
        abstract = True
