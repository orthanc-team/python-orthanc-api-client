import orthanc
import json
from pydicom.uid import generate_uid
from typing import List
import pydicom

from io import BytesIO

from pydicom import dcmread, dcmwrite
from pydicom.filebase import DicomFileLike


TOKEN = orthanc.GenerateRestApiAuthorizationToken()


def write_dataset_to_bytes(dataset):
    # create a buffer
    with BytesIO() as buffer:
        # create a DicomFileLike object that has some properties of DataSet
        memory_dataset = DicomFileLike(buffer)
        # write the dataset to the DicomFileLike object
        dcmwrite(memory_dataset, dataset)
        # to read from the object, you have to rewind it
        memory_dataset.seek(0)
        # read the contents as bytes
        return memory_dataset.read()



def get_api_token(output, uri, **request):
    # unsafe !!!!  don't expose the token on a Rest API !!!! (don't run this experiment at home !)
    output.AnswerBuffer(TOKEN, 'text/plain')



def worklist_callback(answers, query, issuerAet, calledAet):
    global worklist_handler

    orthanc.LogInfo(f'Received incoming C-FIND worklist request from {issuerAet} - calledAet={calledAet}')

    # Get a memory buffer containing the DICOM instance
    dicom = query.WorklistGetDicomQuery()
    json_tags = json.loads(orthanc.DicomBufferToJson(dicom, orthanc.DicomToJsonFormat.FULL, orthanc.DicomToJsonFlags.NONE, 0))

    dataset = pydicom.dataset.Dataset()
    dataset.is_little_endian = True
    dataset.is_implicit_VR = False
    dataset.AccessionNumber = 'A123456'
    dataset.StudyInstanceUID = '1.2.3.4'
    dataset.PatientName = 'PatientName'
    dataset.PatientID = 'PatientID'
    dataset.PatientBirthDate = '20220208'
    dataset.PatientSex = 'O'

    dataset_bytes = write_dataset_to_bytes(dataset)

    answers.WorklistAddAnswer(query, dataset_bytes)


orthanc.RegisterWorklistCallback(worklist_callback)
orthanc.RegisterRestCallback('/api-token', get_api_token)
