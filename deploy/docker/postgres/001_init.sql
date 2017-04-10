-- drop database if exists seqrdb;
-- drop database if exists xwiki;

create database seqrdb;
create database xwiki;

grant all privileges on database seqrdb to postgres;
grant all privileges on database xwiki to postgres;
