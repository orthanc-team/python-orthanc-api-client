
from .resources import Resources
from .exceptions import *


class Studies(Resources):

    def __init__(self, api_client: 'OrthancApiClient'):
        super().__init__(api_client=api_client, url_segment='studies')


    def find(self, StudyInstanceUID: str) -> str:
        """
        finds a study in Orthanc based on its StudyInstanceUid

        Returns
        -------
        the instance id of the study or None if not found
        """
        study_ids = self._api_client.lookup(needle=StudyInstanceUID, filter='Study')
        if len(study_ids) == 1:
            return study_ids[0]

        if len(study_ids) > 1:
            raise TooManyResourcesFound()        
        return None
