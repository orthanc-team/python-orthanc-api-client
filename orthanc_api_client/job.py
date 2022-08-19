from strenum import StrEnum
from .helpers import wait_until

class JobType(StrEnum):

    DICOM_WEB_STOW_CLIENT = 'DicomWebStowClient'
    DICOM_MOVE_SCU = 'DicomMoveScu'
    DICOM_MODALITY_STORE = 'DicomModalityStore'
    MEDIA = 'Media'
    ARCHIVE = 'Archive'
    MERGE_STUDY = 'MergeStudy'
    SPLIT_STUDY = 'SplitStudy'
    ORTHANC_PEER_STORE = 'OrthancPeerStore'
    RESOURCE_MODIFICATION = 'ResourceModification'
    STORAGE_COMMITMENT_SCP = 'StorageCommitmentScp'
    PUSH_TRANSFER = "PushTransfer"
    PULL_TRANSFER = "PullTransfer"


class JobStatus(StrEnum):

    PENDING = 'Pending'
    RUNNING = 'Running'
    SUCCESS = 'Success'
    FAILURE = 'Failure'
    PAUSED = 'Paused'
    RETRY = 'Retry'


class JobInfo:

    def __init__(self, json_job: object):
        self.orthanc_id = json_job.get('ID')
        self.status = json_job.get('State')
        self.type = json_job.get('Type')
        self.content = json_job.get('Content')


class Job:

    def __init__(self, api_client, orthanc_id):
        self._api_client = api_client
        self.orthanc_id = orthanc_id
        self._info = None

    @staticmethod
    def from_json(api_client, json_job: object):
        job = Job(api_client, json_job.get('ID'))
        job._info = JobInfo(json_job)
        return job

    @property
    def info(self):  # lazy loading of job info ....
        if self._info is None:
            self._load_info()
        return self._info

    @property
    def content(self):
        return self._info.content

    def refresh(self) -> "Job":
        self._load_info()
        return self;

    def is_complete(self) -> bool:
        self.refresh()

        return self._info.status in [JobStatus.SUCCESS, JobStatus.FAILURE]

    def wait_completed(self, timeout: float = None, polling_interval: float = 1) -> bool:
        return wait_until(self.is_complete, timeout=timeout, polling_interval=polling_interval)

    def _load_info(self):
        json_job = self._api_client.jobs.get_json(self.orthanc_id)
        self._info = JobInfo(json_job)