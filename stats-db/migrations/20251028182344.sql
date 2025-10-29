-- Create "hourly_edge_requests" table
CREATE TABLE `hourly_edge_requests` (
  `ymd` date NOT NULL,
  `hour` int NOT NULL,
  `node_num` int NOT NULL,
  `access_type` varchar(1) NOT NULL,
  `connections` int NOT NULL,
  PRIMARY KEY (`ymd`, `hour`, `node_num`, `access_type`)
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
