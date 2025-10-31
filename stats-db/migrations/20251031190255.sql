-- Create "historical_hourly_requests" table
CREATE TABLE `historical_hourly_requests` (
  `ymd` date NOT NULL,
  `hour` int NOT NULL,
  `node_num` int NOT NULL,
  `access_type` varchar(1) NOT NULL,
  `connections` int NULL,
  PRIMARY KEY (`ymd`, `hour`, `node_num`, `access_type`)
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
-- Create "request_sources" table
CREATE TABLE `request_sources` (
  `id` tinyint unsigned NOT NULL,
  `description` varchar(255) NULL,
  PRIMARY KEY (`id`)
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
-- Create "hourly_requests" table
CREATE TABLE `hourly_requests` (
  `start_dttm` datetime NOT NULL,
  `source_id` tinyint unsigned NOT NULL,
  `request_count` int NULL,
  PRIMARY KEY (`start_dttm`, `source_id`),
  INDEX `source_id` (`source_id`),
  CONSTRAINT `hourly_requests_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `request_sources` (`id`) ON UPDATE NO ACTION ON DELETE NO ACTION
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
-- Drop "hourly_edge_requests" table
DROP TABLE `hourly_edge_requests`;
