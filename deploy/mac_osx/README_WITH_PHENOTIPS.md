
Integrating PhenoTips with xBrowse
==================================

PhenoTips (https://phenotips.org/) is a xBrowse-external tool that can be used to enter patient phenotype data. Specific code in xBrowse can be activated to add a link next to individuals inside a family to a phenotype record of that patient in an instance of PhenoTips. This capability can be switched on/off as per project that needs it.

To enable this functionality two main adjustments need to be made. First, add patient records with basic information matching individuals in xBrowse and second, add PhenoTips links to user interface (UI).

1. To create a project (usually contained by a PED file) to xBrowse,

python manage.py add_project <some_project_ID>    <some_description_of_project_in_quotes>

2. Add individuals (patients) to that project

python manage.py add_individuals_to_project  <some_project_ID>  --ped  <path_to_associated_PED_file>


3. Now create basic place holder patient records to match individuals in xBrowse:

i. Create a "project" in PhenoTips. Project creation in PhenoTips entails generating two user accounts. One a primary manager role that can edit/view a related group of patients, and the a view only account that get's added to every patient record associated to it. This is done via,

Please remember to use the same <some_project_ID> as you used in xBrowse project that corresponds to these collection of patients ("individuals" in xBrowse).

python manage.py add_project_to_phenotips <some_project_ID>    <some_description_of_project_in_quotes>

ii. Add related patient records to this "project". The manager role we created earlier is able to edit/view these patients and owns them. We add the read-only account to each patient as well. This role is awarded to the user depending on their xBrowse credentials. IE a xBrowse manager would be a PhenoTips manager.This can be done via a PED file using the following command.

python manage.py add_individuals_to_phenotips  <some_project_ID>  --ped  <path_to_associated_PED_file>


PhenoTips links to appear in UI:

1. Follow the instructions to install xBrowse as specified on its website, before starting xBrowse do following,

2. Download PhenoTips and install as instructed on their website https://phenotips.org/Download.

3. Please expose PhenoTips through the 9010 port number. For example, if you are using the *.zip file: while logged into the host machine where PhenoTips would run,
export JETTY_PORT=9010

4. If you plan to run PhenoTips in a screen session or as nohup, you will need to add the following new Java option to start.sh

START_OPTS="$START_OPTS -Djava.awt.headless=true"
 

5. Start PhenoTips as instructed on their website and specific installation instruction (https://phenotips.org/Download)

6. Go to settings.py in the xBrowse installation directory. There is a tuple named PHENOTIPS_SUPPORTED_PROJECTS at the bottom of this file that specifies which xBrowse project should get PhenoTips links next to the individual in the family. Add your project to this tuple for the link to appear.

For example, the following should add project "1kg" to PhenoTips system UI.
PHENOTIPS_SUPPORTED_PROJECTS = (
                       '1kg',
                       )
                       
7. Start xBrowse.



                
Switching the back-end database in PhenoTips to Postgresql
=========================================================

The default database that comes with the zip distribution of PhenoTips is HSQLDB. For large scale deployments the PhenoTips developers recommend an alternate database system. To swap in Postgresql the following needs to be done.


A. Get the Postgresql database ready:

1. Install Postgresql as instructed on their website on your platform.

2. Create a directory to put database files.
mkdir postgres_data_dir  
              
3. Initialize a database using the default administrator user
initdb -D postgres_data_dir -U postgres

4. Start postgresql server
pg_ctl -D postgres_data_dir -l logfile start

5. Connect as root
psql -U postgres

6. Create a user name for PhenoTips to use
create user xwiki with password 'xwiki';

7. Create a database for PhenoTips to use
create database xwiki owner xwiki;

8. Connect to that database and create a schema in it for PhenoTips to use
\connect xwiki;
CREATE SCHEMA AUTHORIZATION xwiki;


B. Re-wire PhenoTips to use the new database. 3 Files need to be modified.

1.Update configuration files,
i.  hibernate.cfg.xml:
First adjust hibernate.cfg.xml to use Postgresql instead of HSQLDB (comment and uncomment appropriately). Fill in the username/pwd/db/schema names you used, for example,

    <property name="connection.url">jdbc:postgresql:xwiki</property>
    <property name="connection.username">xwiki</property>
    <property name="connection.password">xwiki</property>
    <property name="connection.driver_class">org.postgresql.Driver</property>
    <property name="dialect">org.hibernate.dialect.PostgreSQLDialect</property>
    <property name="jdbc.use_streams_for_binary">false</property>
    <property name="xwiki.virtual_mode">schema</property>
    <mapping resource="xwiki.postgresql.hbm.xml"/>
    <mapping resource="feeds.hbm.xml"/>
   

ii. xwiki.cfg
Change the xwiki.db value to reflect the name of the DB you picked,
For example uncomment,
xwiki.db=xwiki


iii.xwiki.properties
Change the environment variable here to point to where you want the PhenoTips work directory to live.
For example,
environment.permanentDirectory=/dev/sandbox/phenotips_postgres/phenotips_work_dir


2. Copy over the newest JDBC driver for Postgresql and put it in WEB-INF/lib/

3. Find all files with the extension ".xed" and modify the following line to be "false" from "true"

For example, change following,

<installed.installed type="boolean">true</installed.installed>
to,
<installed.installed type="boolean">false</installed.installed>

C. Now start PhenoTips

D. Go to the UI and follow the instructions to install all required tables to Postgresql.

Other instructions (not specific to Postgresql as of this writing) can also be found at the PhenoTips pages at,
https://phenotips.org/AdminGuide/Installation







