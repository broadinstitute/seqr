/**
 * Given a patient ID (NAxxx,) show the phenotips edit page for it
 **/
function showEditPageForThisPatient(patientId) {
	var uri = '/api/phenotips/proxy/edit/' + patientId;
	$('#phenotipsEditPatientFrame').attr('src', uri);
	$('#phenotipsModal').modal('show');
}