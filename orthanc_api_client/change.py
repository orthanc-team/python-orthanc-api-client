from enum import Enum
from strenum import StrEnum
from dataclasses import dataclass
from datetime import datetime

class ResourceType(StrEnum):

    PATIENT = 'Patient'
    STUDY = 'Study'
    SERIES = 'Series'
    INSTANCE = 'Instance'

class ChangeType(StrEnum):

    NEW_INSTANCE = 'NewInstance'
    NEW_SERIES = 'NewSeries'
    NEW_STUDY = 'NewStudy'
    NEW_PATIENT = 'NewPatient'
    STABLE_SERIES = 'StableSeries'
    STABLE_STUDY = 'StableStudy'
    STABLE_PATIENT = 'StablePatient'


@dataclass
class Change:

    resource_type: ResourceType
    change_type: ChangeType
    sequence_id: int
    resource_id: str
    timestamp: datetime

    def __str__(self):
        return f"[{self.sequence_id:09}] {self.timestamp}: {self.change_type} - {self.resource_id}"
