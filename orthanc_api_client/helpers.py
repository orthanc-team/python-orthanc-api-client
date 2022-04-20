import time
from io import BytesIO

import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian
from pydicom.filebase import DicomFileLike
from pydicom import dcmread, dcmwrite
import pydicom._storage_sopclass_uids


def wait_until(somepredicate, timeout, period=0.1, *args, **kwargs):
  
  if timeout is None:
    while True:
        if somepredicate(*args, **kwargs): 
            return True
        time.sleep(period)
    return False      
  else:
    mustend = time.time() + timeout
    while time.time() < mustend:
        if somepredicate(*args, **kwargs): 
            return True
        time.sleep(period)
    return False


def write_dataset_to_bytes(dataset) -> bytes:
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


def generate_test_dicom_file(
        width: int = 128,
        height: int = 128,
        tags: any = {}
        ) -> bytes:
    buffer = bytearray(height * width * 2)

    meta = pydicom.Dataset()
    meta.MediaStorageSOPClassUID = pydicom._storage_sopclass_uids.MRImageStorage
    meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian  

    ds = Dataset()
    ds.file_meta = meta

    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.Modality = "MR"
    ds.SOPInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.FrameOfReferenceUID = pydicom.uid.generate_uid()

    ds.PatientName = "Test^Patient^Name"
    ds.PatientID = "Test-Patient-ID"
    ds.PatientSex = "U"
    ds.PatientBirthDate = "20000101"

    ds.ImagesInAcquisition = "1"
    ds.InstanceNumber = 1
    ds.ImagePositionPatient = r"0\0\1"
    ds.ImageOrientationPatient = r"1\0\0\0\-1\0"
    ds.ImageType = r"ORIGINAL\PRIMARY\AXIAL"

    ds.RescaleIntercept = "0"
    ds.RescaleSlope = "1"
    ds.PixelSpacing = r"1\1"
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelRepresentation = 1

    if ds.Modality == "MR":
        ds.SOPClassUID = pydicom._storage_sopclass_uids.MRImageStorage
    elif ds.Modality == "CT":
        ds.SOPClassUID = pydicom._storage_sopclass_uids.CTImageStorage
    elif ds.Modality == "CR":
        ds.SOPClassUID = pydicom._storage_sopclass_uids.ComputedRadiographyImageStorage
    elif ds.Modality == "DX":
        ds.SOPClassUID = pydicom._storage_sopclass_uids.DigitalXRayImageStorageForPresentation
    else:
        raise NotImplementedError

    # copy tags values in the dataset
    for (k, v) in tags.items():
        ds.__setattr__(k, v)


    ds.BitsStored = 16
    ds.BitsAllocated = 16
    ds.SamplesPerPixel = 1
    ds.HighBit = 15

    ds.Rows = height
    ds.Columns = width

    pydicom.dataset.validate_file_meta(ds.file_meta, enforce_standard=True)

    ds.PixelData = bytes(buffer)

    return write_dataset_to_bytes(ds)
