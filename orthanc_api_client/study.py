from .tags import SimplifiedTags


class StudyInfo:

    def __init__(self, json_study: object):
        self.main_dicom_tags = SimplifiedTags(json_study.get('MainDicomTags'))
        self.patient_main_dicom_tags = SimplifiedTags(json_study.get('PatientMainDicomTags'))
        self.orthanc_id = json_study.get('ID')
        self.dicom_id = self.main_dicom_tags.get('StudyInstanceUID')
        self.series_ids = json_study.get('Series')


class Study:

    def __init__(self, api_client, orthanc_id):
        self._api_client = api_client
        self.orthanc_id = orthanc_id
        self._info = None

    @staticmethod
    def from_json(api_client, json_study: object):
        study = Study(api_client, json_study.get('ID'))
        study._info = StudyInfo(json_study)
        return study

    @property
    def info(self):  # lazy loading of main dicom tags ....
        if self._info is None:
            self._load_info()
        return self._info

    @property
    def main_dicom_tags(self):
        return self.info.main_dicom_tags

    @property
    def patient_main_dicom_tags(self):
        return self.info.patient_main_dicom_tags

    @property
    def dicom_id(self):
        return self.info.dicom_id

    def _load_info(self):
        json_study = self._api_client.studies.get_json(self.orthanc_id)
        self._info = StudyInfo(json_study)

