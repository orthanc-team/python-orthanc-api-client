import orthanc
import json
from pydicom.uid import generate_uid
from typing import List
import pydicom
import time

from io import BytesIO


TOKEN = orthanc.GenerateRestApiAuthorizationToken()


def write_dataset_to_bytes(dataset):
    # create a buffer
    with BytesIO() as buffer:
        dataset.save_as(buffer)
        return buffer.getvalue()


def get_api_token(output, uri, **request):
    # unsafe !!!!  don't expose the token on a Rest API !!!! (don't run this experiment at home !)
    output.AnswerBuffer(TOKEN, 'text/plain')


def get_sleep(output, uri, **request):
    duration = request['groups'][0]
    orthanc.LogInfo(f"Entering sleep of {duration} sec")
    time.sleep(float(duration))
    output.AnswerBuffer("that was a good sleep", 'text/plain')
    orthanc.LogInfo(f"Exited sleep of {duration} sec")


def worklist_callback(answers, query, issuerAet, calledAet):
    global worklist_handler

    orthanc.LogInfo(f'Received incoming C-FIND worklist request from {issuerAet} - calledAet={calledAet}')

    # Get a memory buffer containing the DICOM instance
    dicom = query.WorklistGetDicomQuery()
    json_tags = json.loads(orthanc.DicomBufferToJson(dicom, orthanc.DicomToJsonFormat.FULL, orthanc.DicomToJsonFlags.NONE, 0))

    dataset = pydicom.dataset.Dataset()

    file_meta = pydicom.dataset.FileMetaDataset()

    # Set the FileMeta attributes
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.31'
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = '1.2.840.10008.5.1.4.1.1.2'
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    dataset.file_meta = file_meta

    # dataset.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    dataset.AccessionNumber = 'A123456'
    dataset.StudyInstanceUID = '1.2.3.4'
    dataset.PatientName = 'PatientName'
    dataset.PatientID = 'PatientID'
    dataset.PatientBirthDate = '20220208'
    dataset.PatientSex = 'O'
    # dataset.is_little_endian = True
    # dataset.is_implicit_VR = False
    # dataset.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    dataset_bytes = write_dataset_to_bytes(dataset)

    answers.WorklistAddAnswer(query, dataset_bytes)


orthanc.RegisterWorklistCallback(worklist_callback)
orthanc.RegisterRestCallback('/api-token', get_api_token)
orthanc.RegisterRestCallback('/sleep/(.*)', get_sleep)
