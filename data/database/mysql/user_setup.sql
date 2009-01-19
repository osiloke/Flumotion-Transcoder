-- This is the user setup information for platform database VERSION 20081230

-- These 3 lines are because mysql installations sometimes have entries
-- by default that include host localhost or 127.0.0.1 and an empty user
-- which match first before any with a host of '%' so users cannot access
-- from localhost or 127.0.0.1
delete from mysql.user where host='localhost' AND user='';
delete from mysql.user where host='127.0.0.1' and user='';
flush privileges;
grant insert, select, update, delete on transcoder_reports to 'transcoder'@'%' identified by 'transcoderpass';
flush privileges;
