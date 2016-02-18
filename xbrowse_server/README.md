====
Installation
====
pip install django
pip install south
pip install pytz
pip install django-extensions


=== 
Relation to xbrowse
===
The following models are stored on both the server DB and either datastore or reference. 
The idea is that the primary source is either reference or datastore, but they are mirrored on the server because it needs to add some extra information. 

Datastore: 
- Family
