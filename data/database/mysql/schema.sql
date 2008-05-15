###  The whole schema for the transcoder database VERSION 2008051400

CREATE TABLE IF NOT EXISTS `schema_information` (
	`schema_version` int(9) NOT NULL,
    `upgrading_soon` BOOL default 0,
    `upgrading_currently` BOOL default 0
) type=InnoDB;

CREATE TABLE IF NOT EXISTS `reports_targets` (
  `customer_id` int(11) default NULL,
  `creation_time` datetime default NULL,  
  `filepath` varchar(256) default NULL,
  `bitrate` int(5) default NULL,
  KEY `customer_id` (`customer_id`),
  KEY `creation_time` (`creation_time`),
  KEY `filepath` (`filepath`)
) type=InnoDB; 
