from dataclasses import dataclass


class Capabilities:


    def __init__(self, api_client: 'OrthancApiClient'):
        self._api_client = api_client
        self._system_json = None

    @property
    def _system_info(self):
        if not self._system_json:
            self._system_json = self._api_client.get_system()
        return self._system_json
    @property
    def has_extended_find(self) -> bool:
        return "Capabilities" in self._system_info and self._system_info["Capabilities"].get("HasExtendedFind")

    @property
    def has_extended_changes(self) -> bool:
        return "Capabilities" in self._system_info and self._system_info["Capabilities"].get("HasExtendedChanges")

    @property
    def has_label_support(self) -> bool:
        return self._system_info["HasLabels"]

    @property
    def has_revision_support(self) -> bool:
        return self._system_info["CheckRevisions"]
