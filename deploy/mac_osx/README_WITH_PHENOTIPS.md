
Integrating PhenoTips with xBrowse
==================================

PhenoTips (https://phenotips.org/) is an xBrowse-external tool that can be used to enter patient phenotype data. Specific code in xBrowse can be activated to add a link next to individuals inside a family to a phenotype record of that patient in an instance of PhenoTips. This capability can be switched on/off as per project that needs it.

To enable this functionality two main adjustments need to be made. First, add patient records with basic information matching individuals in xBrowse and second, add PhenoTips links to user interface (UI).


Create basic patient records to match individuals in xBrowse:
1. Create a "project" in PhenTips. Project creation in PhenoTips entails generating two user accounts. One a primary manager role that can edit/view a related group of patients, and the a view only account that get's added to every patient record associated to it. This is done via,

python manage.py add_project <some_project_ID>    <some_description_of_project_in_quotes>

2. Add related patient records to this "project". The manager role we created earlier is able to edit/view these patients and owns them. We add the read-only account to each patient as well. This role is awarded to the user depending on their xBrowse credentials. IE a xBrowse manager would be a PhenoTips manager.This can be done via a PED file using the following command.

python manage.py add_individuals_to_phenotips.py  <some_project_ID>  --ped  <path_to_associated_PED_file>


PhenoTips links to appear in UI:

1. Follow the instructions to install xBrowse as specified at <link>, before starting xBrowse do following,

2. Download PhenoTips and install as instructed on their website https://phenotips.org/Download.

2. Please expose PhenoTips through the 9010 port number. For example, if you are using the *.zip file: while logged into the host machine where PhenoTips would run,
export JETTY_PORT=9010

3. Start PhenoTips as instructed on their website and specific installation instruction (https://phenotips.org/Download)

4. Go to settings.py in the xBrowse installation directory. There is a tuple named PHENOTIPS_SUPPORTED_PROJECTS at the bottom of this file that specifies which xBrowse project should get PhenoTips links next to the individual in the family. Add your project to this tuple for the link to appear.

For example, the following should add project "1kg" to PhenoTips system UI.
PHENOTIPS_SUPPORTED_PROJECTS = (
                       '1kg',
                       )
                       
5. Start xBrowse.
                       
                       
            


