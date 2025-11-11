-- Modify "hourly_requests" table
ALTER TABLE `hourly_requests` RENAME INDEX `hourly_requests_ibfk_1` TO `source_id`;
