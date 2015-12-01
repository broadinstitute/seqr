/**
 * Given a patient ID (NAxxx,) show the phenotips edit page for it
 **/
function showEditPageForThisPatient(patientId,project) {
	var uri = '/api/phenotips/proxy/edit/' + patientId + '?' + 'project=' + project;
	$('#phenotipsEditPatientFrame').attr('src', uri);
	$('#phenotipsModal').modal('show');
}