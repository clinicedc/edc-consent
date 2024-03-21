from __future__ import annotations

import sys
from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from django.apps import apps as django_apps
from django.core.management.color import color_style
from django.utils.module_loading import import_module, module_has_submodule
from edc_utils import floor_secs, formatted_date
from edc_utils.date import floor_datetime

from .exceptions import (
    AlreadyRegistered,
    ConsentDefinitionDoesNotExist,
    ConsentDefinitionError,
    SiteConsentError,
)

if TYPE_CHECKING:
    from edc_model.models import BaseUuidModel
    from edc_sites.single_site import SingleSite

    from .consent_definition import ConsentDefinition
    from .model_mixins import ConsentModelMixin

    class ConsentModel(ConsentModelMixin, BaseUuidModel): ...


__all__ = ["site_consents"]


class SiteConsents:
    def __init__(self):
        self.registry = {}
        self.loaded = False

    def register(
        self, cdef: ConsentDefinition, updated_by: ConsentDefinition | None = None
    ) -> None:
        cdef.updated_by = updated_by
        if cdef.name in self.registry:
            raise AlreadyRegistered(f"Consent definition already registered. Got {cdef.name}.")
        self.validate_period_overlap_or_raise(cdef)
        self.validate_updates_or_raise(cdef)
        self.registry.update({cdef.name: cdef})
        self.loaded = True

    def get_registry_display(self):
        cdefs = sorted(list(self.registry.values()), key=lambda x: x.version)
        return "', '".join([cdef.display_name for cdef in cdefs])

    def get(self, name) -> ConsentDefinition:
        return self.registry.get(name)

    def all(self) -> list[ConsentDefinition]:
        return sorted(list(self.registry.values()), key=lambda x: x.version)

    def validate_updates_or_raise(self, cdef: ConsentDefinition) -> None:
        if cdef.updates:
            if cdef.updates not in self.registry.values():
                raise ConsentDefinitionError(
                    f"Updates unregistered consent definition. See {cdef.name}. "
                    f"Got {cdef.updates.name}"
                )
            elif cdef.updates and cdef.updates.updated_by is None:
                raise ConsentDefinitionError(
                    f"Cdef mismatch with consent definition configured to update another. "
                    f"'{cdef.name}' is configured to update "
                    f"'{cdef.updates.name}' but '{cdef.updates.name}' "
                    f"updated_by is None. "
                )
            elif cdef.updates and cdef.updates.updated_by != cdef:
                raise ConsentDefinitionError(
                    f"Cdef mismatch with consent definition configured to update another. "
                    f"'{cdef.name}' is configured to update "
                    f"'{cdef.updates.name}' but '{cdef.updates.name}' "
                    f"updated_by='{cdef.updates.updated_by.name}' not '{cdef.name}'. "
                )

    def validate_period_overlap_or_raise(self, cdef: ConsentDefinition):
        for registered_cdef in self.registry.values():
            if (
                cdef
                and cdef.validate_duration_overlap_by_model
                and registered_cdef.proxy_model == cdef.proxy_model
            ):
                if (
                    registered_cdef.start <= cdef.start <= registered_cdef.end
                    or registered_cdef.start <= cdef.end <= registered_cdef.end
                ):
                    raise ConsentDefinitionError(
                        f"Consent period overlaps with an already registered consent "
                        f"definition. See already registered consent {registered_cdef.name}. "
                        f"Got {cdef.name}."
                    )

    def get_consent_definition(
        self,
        model: str = None,
        report_datetime: datetime | None = None,
        version: str | None = None,
        site: SingleSite | None = None,
        screening_model: str | None = None,
        **kwargs,
    ) -> ConsentDefinition:
        """Returns a single consent definition valid for the given criteria.

        Filters the registry by each param given.
        """
        cdefs = self.get_consent_definitions(
            model=model,
            report_datetime=report_datetime,
            version=version,
            site=site,
            screening_model=screening_model,
            **kwargs,
        )
        if len(cdefs) > 1:
            as_string = ", ".join(list(set([cdef.name for cdef in cdefs])))
            raise SiteConsentError(f"Multiple consent definitions returned. Got {as_string}. ")
        return cdefs[0]

    def get_consent_definitions(
        self,
        model: str = None,
        report_datetime: datetime | None = None,
        version: str | None = None,
        site: SingleSite | None = None,
        screening_model: str | None = None,
        **kwargs,
    ) -> list[ConsentDefinition]:
        """Return a list of consent definitions valid for the given
        criteria.

        Filters the registry by each param given.
        """
        error_messages: list[str] = []
        # confirm loaded
        if not self.registry.values() or not self.loaded:
            raise SiteConsentError(
                "No consent definitions have been registered with `site_consents`. "
            )
        # copy registry
        cdefs: list[ConsentDefinition] = [cdef for cdef in self.registry.values()]
        # filter cdefs to try to get just one.
        # by model, report_datetime, version, site
        cdefs, error_msg = self._filter_cdefs_by_model_or_raise(model, cdefs, error_messages)
        cdefs, error_msg = self._filter_cdefs_by_report_datetime_or_raise(
            report_datetime, cdefs, error_messages
        )
        cdefs, error_msg = self._filter_cdefs_by_version_or_raise(
            version, cdefs, error_messages
        )
        cdefs = self.filter_cdefs_by_site_or_raise(site, cdefs, error_messages)

        cdefs, error_msg = self._filter_cdefs_by_model_or_raise(
            screening_model, cdefs, error_messages, attrname="screening_model"
        )

        # apply additional criteria
        for k, v in kwargs.items():
            if v is not None:
                cdefs = [cdef for cdef in cdefs if getattr(cdef, k) == v]
        return sorted(cdefs, key=lambda x: x.version)

    @staticmethod
    def _filter_cdefs_by_model_or_raise(
        model: str | None,
        consent_definitions: list[ConsentDefinition],
        errror_messages: list[str] = None,
        attrname: str | None = None,
    ) -> tuple[list[ConsentDefinition], list[str]]:
        attrname = attrname or "model"
        cdefs = consent_definitions
        if model:
            cdefs = [cdef for cdef in cdefs if model == getattr(cdef, attrname)]
            if not cdefs:
                raise ConsentDefinitionDoesNotExist(
                    f"There are no consent definitions using this model. Got {model}."
                )
            else:
                errror_messages.append(f"model={model}")
        return cdefs, errror_messages

    def _filter_cdefs_by_report_datetime_or_raise(
        self,
        report_datetime: datetime | None,
        consent_definitions: list[ConsentDefinition],
        errror_messages: list[str] = None,
    ) -> tuple[list[ConsentDefinition], list[str]]:
        cdefs = consent_definitions
        if report_datetime:
            cdefs = [
                cdef
                for cdef in cdefs
                if floor_secs(floor_datetime(cdef.start))
                <= floor_secs(floor_datetime(report_datetime))
                <= floor_secs(floor_datetime(cdef.end))
            ]
            if not cdefs:
                date_string = formatted_date(report_datetime)
                using_msg = "Using " + " and ".join(errror_messages)
                raise ConsentDefinitionDoesNotExist(
                    "Date does not fall within the validity period of any consent definition. "
                    f"Got {date_string}. {using_msg}. Consent definitions are: "
                    f"{self.get_registry_display()}."
                )
            else:
                date_string = formatted_date(report_datetime)
                errror_messages.append(f"report_datetime={date_string}")
        return cdefs, errror_messages

    def _filter_cdefs_by_version_or_raise(
        self,
        version: str | None,
        consent_definitions: list[ConsentDefinition],
        errror_messages: list[str] = None,
    ) -> tuple[list[ConsentDefinition], list[str]]:
        cdefs = consent_definitions
        if version:
            cdefs = [cdef for cdef in cdefs if cdef.version == version]
            if not cdefs:
                using_msg = "Using " + " and ".join(errror_messages)
                errror_messages.append(f"version={version}")
                raise ConsentDefinitionDoesNotExist(
                    f"There are no consent definitions for this version. "
                    f"Got {version}. {using_msg}. "
                    f"Consent definitions are: {self.get_registry_display()}."
                )
        return cdefs, errror_messages

    def filter_cdefs_by_site_or_raise(
        self,
        site: SingleSite | None,
        consent_definitions: list[ConsentDefinition],
        errror_messages: list[str] = None,
    ) -> list[ConsentDefinition]:
        cdefs = consent_definitions
        if site:
            cdefs_copy = [cdef for cdef in consent_definitions]
            cdefs = []
            for cdef in cdefs_copy:
                if site.site_id in [s.site_id for s in cdef.sites]:
                    cdefs.append(cdef)
            if not cdefs:
                using_msg = "Using " + " and ".join(errror_messages)
                raise ConsentDefinitionDoesNotExist(
                    f"There are no consent definitions for this site. "
                    f"Got {site}. {using_msg}."
                    f"Consent definitions are: {self.get_registry_display()}."
                )
        return cdefs

    def versions(self):
        return [cdef.version for cdef in self.registry.values()]

    def autodiscover(self, module_name=None, verbose=True):
        """Autodiscovers consent classes in the consents.py file of
        any INSTALLED_APP.
        """
        before_import_registry = None
        module_name = module_name or "consents"
        writer = sys.stdout.write if verbose else lambda x: x
        style = color_style()
        writer(f" * checking for site {module_name} ...\n")
        for app in django_apps.app_configs:
            writer(f" * searching {app}           \r")
            try:
                mod = import_module(app)
                try:
                    before_import_registry = deepcopy(site_consents.registry)
                    import_module(f"{app}.{module_name}")
                    writer(f" * registered consent definitions '{module_name}' from '{app}'\n")
                except SiteConsentError as e:
                    writer(f"   - loading {app}.consents ... ")
                    writer(style.ERROR(f"ERROR! {e}\n"))
                except ImportError as e:
                    site_consents.registry = before_import_registry
                    if module_has_submodule(mod, module_name):
                        raise SiteConsentError(str(e))
            except ImportError:
                pass
        for cdef in self.registry.values():
            start = cdef.start.strftime("%Y-%m-%d %Z")
            end = cdef.end.strftime("%Y-%m-%d %Z")
            sys.stdout.write(f"   - {cdef.name} valid {start} to {end}\n")


site_consents = SiteConsents()
