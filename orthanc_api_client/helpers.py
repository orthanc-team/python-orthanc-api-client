import time
import re

import pydicom
import datetime
import random
from .helpers_internal import write_dataset_to_bytes
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian
import pydicom._storage_sopclass_uids


def wait_until(somepredicate, timeout, period=0.1, *args, **kwargs) -> bool:
  
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


def get_random_dicom_date(date_from: datetime.date, date_to: datetime.date = datetime.date.today()) -> str:
    delta = date_to - date_from
    rand_date = date_from + datetime.timedelta(days=random.randint(0, delta.days))
    return '{0:4}{1:02}{2:02}'.format(rand_date.year, rand_date.month, rand_date.day)


def to_dicom_date(date: datetime.date) -> str:
    return '{0:4}{1:02}{2:02}'.format(date.year, date.month, date.day)


def from_dicom_date(dicom_date: str) -> datetime.date:
    if dicom_date is None or len(dicom_date) == 0:
        return None

    m = re.match('(?P<year>[0-9]{4})(?P<month>[0-9]{2})(?P<day>[0-9]{2})', dicom_date)
    if m is None:
        raise ValueError("Not a valid DICOM date: '{0}'".format(dicom_date))

    return datetime.date(int(m.group('year')), int(m.group('month')), int(m.group('day')))


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
