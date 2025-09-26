-- Create "hourly_downloads" table
CREATE TABLE `hourly_downloads` (
  `country` varchar(255) NOT NULL,
  `download_type` varchar(16) NOT NULL,
  `archive` varchar(16) NULL,
  `category` varchar(32) NOT NULL,
  `primary_count` int NULL,
  `cross_count` int NULL,
  `start_dttm` datetime NOT NULL,
  PRIMARY KEY (`country`, `download_type`, `category`, `start_dttm`)
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
