-- Create "monthly_downloads" table
CREATE TABLE `monthly_downloads` (
  `month` date NOT NULL,
  `downloads` int NULL,
  PRIMARY KEY (`month`)
) CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
