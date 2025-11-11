-- Create "monthly_submissions" table
CREATE TABLE `monthly_submissions` (
  `month` date NOT NULL,
  `count` int NOT NULL,
  PRIMARY KEY (`month`)
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
-- Drop "monthly_downloads" table
DROP TABLE `monthly_downloads`;
