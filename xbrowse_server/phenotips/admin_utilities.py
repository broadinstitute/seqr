"""
A series of functions to help with administering PhenoTips
"""

from xbrowse_server.phenotips.utilities import get_uname_pwd_for_project
from django.conf import settings
import requests
import os


def fetch_project_phenotips_patient_ids(project_id):
    """
    Find all patients IDs (external) belonging to this project

    Inputs:
      1. A project ID
      Outputs:
      1. A list of IDs (ex: P0000138) of patients belonging to this
    """
    uname, pwd = get_uname_pwd_for_project(project_id, read_only=False)
    url = settings.PHENOPTIPS_HOST_NAME + '/rest/patients?number=100000'
    headers = {'Accept': 'application/json'}
    r = requests.get(url, headers=headers, auth=(uname, pwd))
    patient_data = r.json()
    patient_ids = []
    for patient_summary in patient_data['patientSummaries']:
        patient_ids.append(patient_summary['id'])
    return patient_ids


def delete_these_phenotips_patient_ids(project_id, patient_ids, is_external_id=False):
    """
    Deletes the input list of patient IDs

      Inputs:
      1.A list of patient ids  (ex: [P0000138, P0000134,..]

      Outputs:
      A list of True/False of all patients were deleted
    """
    for p in patient_ids:
        delete_phenotips_patient_id(project_id, p, is_external_id=is_external_id)


def delete_phenotips_patient_id(project_id, patient_id, is_external_id=False):
    """
    Deletes a single PhenoTips patient ID

    Inputs:
      1. A single patient id  (ex:P0000134)

    Outputs:
      True if success, raises exception otherwise
    """
    uname, pwd = get_uname_pwd_for_project(project_id, read_only=False)
    if is_external_id:
        base_uri = settings.PHENOPTIPS_HOST_NAME + '/rest/patients/eid/'
    else:
        base_uri = settings.PHENOPTIPS_HOST_NAME + '/rest/patients/'
    url = os.path.join(base_uri, patient_id)
    print url
    r = requests.delete(url, auth=(uname, pwd))
    if r.status_code == 204:
        print 'deleted phenotips patient', patient_id, '....'
        return True
