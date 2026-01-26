-- Modify "hourly_downloads" table
ALTER TABLE `hourly_downloads` DROP COLUMN `month`, DROP PRIMARY KEY, ADD PRIMARY KEY (`start_dttm`, `category`, `country`, `download_type`);
