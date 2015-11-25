#create a patient record in phenotips
def create_patient_record(self,individual_id):
  '''make a patient record'''
  uri = os.path.join(settings.PHENOPTIPS_HOST_NAME,'/bin/PhenoTips/OpenPatientRecord?create=true&eid=' + individual_id)
  
      