from __future__ import annotations

from datetime import datetime
from typing import Any

from django import forms
from django.conf import settings
from edc_screening.form_validator_mixins import SubjectScreeningFormValidatorMixin
from edc_utils import AgeValueError, age
from edc_utils.date import to_local, to_utc
from edc_utils.text import convert_php_dateformat


class SubjectConsentFormValidatorMixin(SubjectScreeningFormValidatorMixin):

    """Form Validator mixin for the consent model."""

    def __init__(self: Any, **kwargs):
        super().__init__(**kwargs)
        self._consent_datetime = None
        self.dob = self.cleaned_data.get("dob")
        self.gender = self.cleaned_data.get("gender")
        self.guardian_name = self.cleaned_data.get("guardian_name")

    def _clean(self) -> None:
        self.validate_consent_datetime()
        self.validate_age()
        self.validate_gender()
        self.validate_identity()
        super()._clean()

    @property
    def consent_datetime(self) -> datetime | None:
        if not self._consent_datetime:
            if "consent_datetime" in self.cleaned_data:
                if self.add_form and not self.cleaned_data.get("consent_datetime"):
                    raise forms.ValidationError(
                        {"consent_datetime": "This field is required."}
                    )
                self._consent_datetime = to_utc(self.cleaned_data.get("consent_datetime"))
            else:
                self._consent_datetime = self.instance.consent_datetime
        return self._consent_datetime

    @property
    def screening_age_in_years(self) -> int:
        """Returns age in years calculated from dob relative to
        screening datetime"""
        try:
            rdelta = age(self.dob, self.subject_screening.report_datetime.date())
        except AgeValueError as e:
            raise forms.ValidationError(str(e))
        return rdelta.years

    def validate_age(self) -> None:
        """Validate age matches that on the screening form."""
        if self.dob and self.screening_age_in_years != self.subject_screening.age_in_years:
            raise forms.ValidationError(
                {
                    "dob": "Age mismatch. The date of birth entered does "
                    f"not match the age at screening. "
                    f"Expected {self.subject_screening.age_in_years}. "
                    f"Got {self.screening_age_in_years}."
                }
            )

    def validate_gender(self) -> None:
        """Validate gender matches that on the screening form."""
        if self.gender != self.subject_screening.gender:
            raise forms.ValidationError(
                {
                    "gender": "Gender mismatch. The gender entered does "
                    f"not match that reported at screening. "
                    f"Expected '{self.subject_screening.get_gender_display()}'. "
                }
            )

    def validate_consent_datetime(self) -> None:
        """Validate consent datetime with the eligibility datetime.

        Eligibility datetime must come first.

        Watchout for timezone, cleaned_data has local TZ.
        """
        if self.consent_datetime:
            if (
                self.consent_datetime - self.subject_screening.eligibility_datetime
            ).total_seconds() < 0:
                dt_str = to_local(self.subject_screening.eligibility_datetime).strftime(
                    convert_php_dateformat(settings.SHORT_DATETIME_FORMAT)
                )
                raise forms.ValidationError(
                    {
                        "consent_datetime": (
                            f"Cannot be before the date and time eligibility "
                            f"was confirmed. Eligibility was confirmed at "
                            f"{dt_str}."
                        )
                    },
                )

    def validate_identity(self: Any) -> None:
        pass
