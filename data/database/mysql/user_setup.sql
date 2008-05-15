### This is the user setup information for platform database VERSION 2008051400

### These 3 lines are because mysql installations sometimes have entries
### by default that include host localhost or 127.0.0.1 and an empty user
### which match first before any with a host of '%' so users cannot access
### from localhost or 127.0.0.1
DELETE FROM mysql.user WHERE host='localhost' AND user='';
DELETE FROM mysql.user WHERE host='127.0.0.1' AND user='';
FLUSH PRIVILEGES;
GRANT SELECT ON reports_targets TO 'streamer_dev'@'%' IDENTIFIED BY 'streamerpass';
GRANT INSERT,SELECT,UPDATE,DELETE ON reports_targets TO 'transcoder_dev'@'%' IDENTIFIED BY 'transcoderpass';
FLUSH PRIVILEGES;
