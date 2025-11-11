-- Create "monthly_downloads" table
CREATE TABLE `monthly_downloads` (
  `month` date NOT NULL,
  `count` int NOT NULL,
  PRIMARY KEY (`month`)
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
-- Create "requests_source" table
CREATE TABLE `requests_source` (
  `id` tinyint unsigned NOT NULL,
  `description` varchar(255) NULL,
  PRIMARY KEY (`id`)
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
-- Modify "hourly_requests" table
ALTER TABLE `hourly_requests` DROP FOREIGN KEY `hourly_requests_ibfk_1`, DROP INDEX `hourly_requests_ibfk_1`;
-- Modify "hourly_requests" table
ALTER TABLE `hourly_requests` ADD CONSTRAINT `hourly_requests_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `requests_source` (`id`) ON UPDATE NO ACTION ON DELETE NO ACTION;
-- Drop "request_sources" table
DROP TABLE `request_sources`;
