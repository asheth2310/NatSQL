-- 03_roles.sql — dedicated read-only role for the backend.
-- The app can only SELECT from the demo schema; no write access,
-- and no access to mysql.* system tables.
USE demo;

CREATE USER IF NOT EXISTS 'natsql_ro'@'%' IDENTIFIED BY 'natsql_ro_pass';
GRANT SELECT ON demo.* TO 'natsql_ro'@'%';
FLUSH PRIVILEGES;
