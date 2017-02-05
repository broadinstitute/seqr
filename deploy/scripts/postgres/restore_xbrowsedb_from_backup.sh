cd /local/software/seqr

psql -U postgres template1 < <(echo drop database seqrdb)
psql -U postgres template1 < <(echo create database seqrdb)
psql seqrdb < <(gunzip -c ~/xbrowsedb_backup_*.txt.gz)

