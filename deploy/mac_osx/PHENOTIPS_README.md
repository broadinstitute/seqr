
Integrating PhenoTips with seqr
===============================

PhenoTips (https://phenotips.org/) is a seqr-external tool that simplifies the entry of detailed patient phenotype data. It can be installed on the same machine as seqr or on another machine that seqr can access over the network. Once PhenoTips is installed and running, seqr commandline scripts can be used to add seqr families from a given project to PhenoTips. View and Edit Buttons will then appear on seqr family pages in this project. Clicking the buttons will allow users to view or edit the PhenoTips records for individuals in a given family. Currently the PhenoTips integration just allows data to be entered and then viewed. The data is not directly used in analysis.

Installing Phenotips
====================

 1. Download PhenoTips and install as instructed on their website https://phenotips.org/Download

 2. Expose PhenoTips through some port number other than port 80, for example port 9010. To set this up, if you are using the Jetty (rather than Tomcat) setup for PhenoTips, you can set `JETTY_PORT` on the machine where PhenoTips Jetty server will be running:

```
export JETTY_PORT=9010
```

 3. You will also want to add the following to PhenoTips' `start.sh`:
```
START_OPTS="$START_OPTS -Djava.awt.headless=true"
```

 4. Start PhenoTips as instructed on their website (https://phenotips.org/Download)

 5. Edit seqr's `settings.py` file in the seqr installation directory, and update the `PHENOPTIPS_HOST_NAME` value to match the host and port where your PhenoTips instance is running. For example: `http://localhost:9010`


Switching the back-end database in PhenoTips to Postgresql
=========================================================

The default database that comes with the zip distribution of PhenoTips is HSQLDB. For large scale deployments the PhenoTips developers recommend an alternate database system. To swap in Postgresql the following needs to be done.


A. Get the Postgresql database ready:

1. Install Postgresql as instructed on their website on your platform (unless you've already done this as part of the seqr installation)

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

i.  `hibernate.cfg.xml`:
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
   

ii. `xwiki.cfg`
Change the xwiki.db value to reflect the name of the DB you picked,
For example uncomment,
xwiki.db=xwiki


iii. `xwiki.properties`
Change the environment variable here to point to where you want the PhenoTips work directory to live.
For example,
environment.permanentDirectory=/dev/sandbox/phenotips_postgres/phenotips_work_dir


2. Copy over the newest JDBC driver for Postgresql and put it in `WEB-INF/lib/`

3. Find all files with the extension ".xed" and modify the following line to be "false" from "true"

For example, change following,

<installed.installed type="boolean">true</installed.installed>
to,
<installed.installed type="boolean">false</installed.installed>

C. Now start PhenoTips

D. Go to the UI and follow the instructions to install all required tables to Postgresql.

Other instructions (not specific to Postgresql as of this writing) can also be found at the PhenoTips pages at,
https://phenotips.org/AdminGuide/Installation


Enabling Phenotips for a Project
================================

There are several steps to enable the PhenoTips functionality for a project:

1. Create a seqr project if you haven't already:

```
python manage.py add_project <some_project_ID> <some_description_of_project_in_quotes>
python manage.py add_individuals_to_project  <some_project_ID>  --ped  <path_to_associated_PED_file>
```

2. Now add individuals to PhenoTips:

i. Create a "project" in PhenoTips. Project creation in entails generating two PhenoTips user accounts. One a primary manager role that can edit/view a related group of patients, and the a view-only account that gets added to every patient record associated to it. 
This is done via,

```
python2.7 -u manage.py add_project_to_phenotips <some_project_ID> <some_description_of_project_in_quotes>
```

Please remember to use the same <some_project_ID> as you used when creating the seqr project.

ii. Create PhenoTips patients for this project. The manager role we created earlier is able to edit/view these patients and owns them, while the read-only account can only view the patients. The role is awarded to the user depending on their seqr credentials - ie. a seqr user with "manager" permissions get edit access, while a seqr user with "collaborator" permissions gets view-only access. 
The command to run is: 

```
python manage.py generate_ped_file <some_project_ID>     # have seqr generate the ped file for this project
python manage.py add_individuals_to_phenotips  <some_project_ID>  --ped  <path_to_associated_PED_file>
```

