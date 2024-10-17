import time
import re
import pydicom
import datetime
import random
from typing import Union, Optional
from .helpers_internal import write_dataset_to_bytes
import pydicom.uid
from urllib3.filepost import encode_multipart_formdata, choose_boundary


def wait_until(some_predicate, timeout, polling_interval=0.1, *args, **kwargs) -> bool:
  
    if timeout is None:
        while True:
            if some_predicate(*args, **kwargs):
                return True
            time.sleep(polling_interval)
        return False
    else:
        end_time = time.time() + timeout
        while time.time() < end_time:
            if some_predicate(*args, **kwargs):
                return True
            time.sleep(polling_interval)
        return False


def get_random_dicom_date(date_from: datetime.date, date_to: datetime.date = datetime.date.today()) -> str:
    delta = date_to - date_from
    rand_date = date_from + datetime.timedelta(days=random.randint(0, delta.days))
    return '{0:4}{1:02}{2:02}'.format(rand_date.year, rand_date.month, rand_date.day)


def to_dicom_date(date: Union[datetime.date, datetime.datetime]) -> str:
    return '{0:4}{1:02}{2:02}'.format(date.year, date.month, date.day)

def to_dicom_time(dt: datetime.datetime) -> str:
    return '{0:02}{1:02}{2:02}'.format(dt.hour, dt.minute, dt.second)

def to_dicom_time_from_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return to_dicom_time(datetime.datetime.today().replace(hour=hours, minute=minutes, second=seconds))

def from_dicom_date(dicom_date: str) -> datetime.date:
    if dicom_date is None or len(dicom_date) == 0:
        return None

    m = re.match('(?P<year>[0-9]{4})(?P<month>[0-9]{2})(?P<day>[0-9]{2})', dicom_date)
    if m is None:
        raise ValueError("Not a valid DICOM date: '{0}'".format(dicom_date))

    return datetime.date(int(m.group('year')), int(m.group('month')), int(m.group('day')))

def from_dicom_time(dicom_time: str, default: datetime.time = None) -> datetime.time:
    if dicom_time is None or len(dicom_time) == 0:
        if default:
            return default
        else:
            return None

    m = re.match('(?P<hours>[0-9]{2})(?P<minutes>[0-9]{2})(?P<seconds>[0-9]{2})\.(?P<dec>[0-9]{1,6})', dicom_time)
    if m:
        return datetime.time(int(m.group('hours')), int(m.group('minutes')), int(m.group('seconds')),
                             microsecond=int(m.group('dec')) * pow(10, 6 - len(m.group('dec'))))

    m = re.match('(?P<hours>[0-9]{2})(?P<minutes>[0-9]{2})(?P<seconds>[0-9]{2})', dicom_time)
    if m:
        return datetime.time(int(m.group('hours')), int(m.group('minutes')), int(m.group('seconds')))

    m = re.match('(?P<hours>[0-9]{2})(?P<minutes>[0-9]{2})', dicom_time)
    if m:
        return datetime.time(int(m.group('hours')), int(m.group('minutes')), 0)

    m = re.match('(?P<hours>[0-9]{2})', dicom_time)
    if m:
        return datetime.time(int(m.group('hours')), 0, 0)

    if default:
        return default

    raise ValueError("Not a valid DICOM time: '{0}'".format(dicom_time))


def from_orthanc_datetime(orthanc_datetime: str) -> datetime.datetime:
    if orthanc_datetime is None or len(orthanc_datetime) == 0:
        return None

    return datetime.datetime.strptime(orthanc_datetime, "%Y%m%dT%H%M%S")

def from_dicom_date_and_time(dicom_date: str, dicom_time: str) -> datetime.datetime:
    if dicom_date is None or len(dicom_date) == 0:
        return None

    date = from_dicom_date(dicom_date)
    time = from_dicom_time(dicom_time, default=datetime.time(0, 0, 0))

    return datetime.datetime(date.year, date.month, date.day, time.hour, time.minute, time.second, time.microsecond)

def generate_test_dicom_file(
        width: int = 128,
        height: int = 128,
        tags: any = {}
        ) -> bytes:
    buffer = bytearray(height * width * 2)

    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

    ds = pydicom.dataset.Dataset()
    ds.file_meta = file_meta

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
        ds.SOPClassUID = pydicom.uid.MRImageStorage
    elif ds.Modality == "CT":
        ds.SOPClassUID = pydicom.uid.CTImageStorage
    elif ds.Modality == "CR":
        ds.SOPClassUID = pydicom.uid.ComputedRadiographyImageStorage
    elif ds.Modality == "DX":
        ds.SOPClassUID = pydicom.uid.DigitalXRayImageStorageForPresentation
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


def encode_multipart_related(fields, boundary=None):
    if boundary is None:
        boundary = choose_boundary()

    body, _ = encode_multipart_formdata(fields, boundary)
    content_type = str('multipart/related; type=application/dicom; boundary=%s' % boundary)

    return body, content_type


def is_version_at_least(version_string: str, expected_major: int, expected_minor: int, expected_patch: Optional[int] = None) -> bool:
    if version_string.startswith("mainline"):
        return True

    split_version = version_string.split(".")
    if len(split_version) == 0:
        return False

    if len(split_version) >= 1:
        if int(split_version[0]) < expected_major:
            return False

    if len(split_version) >= 2:
        if int(split_version[1]) < expected_minor:
            return False

    if len(split_version) >= 3 and expected_patch is not None:
        if int(split_version[2]) < expected_patch:
            return False
    return True
