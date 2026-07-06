-- Enable CDC on the source database and the customer table (SQL Server / Azure SQL MI).
-- CDC requires the Standard tier or higher. Once enabled, SQL Server maintains change
-- tables that expose inserts/updates/deletes with a log sequence number (__$start_lsn).

-- 1) Enable CDC at the database level.
IF NOT EXISTS (SELECT 1 FROM sys.change_tracking_databases WHERE database_id = DB_ID())
    EXEC sys.sp_cdc_enable_db;
GO

-- 2) Enable CDC on the source table. @role_name = NULL grants access to all readers with
--    SELECT on the table; set a gating role in production.
EXEC sys.sp_cdc_enable_table
    @source_schema = N'dbo',
    @source_name   = N'customer',
    @role_name     = NULL,
    @supports_net_changes = 1;   -- lets the reader pull the net change per key
GO

-- 3) The pipeline reads incrementally with something like:
--    DECLARE @from binary(10) = sys.fn_cdc_map_time_to_lsn('smallest greater than', @watermark);
--    DECLARE @to   binary(10) = sys.fn_cdc_get_max_lsn();
--    SELECT * FROM cdc.fn_cdc_get_all_changes_dbo_customer(@from, @to, N'all');
-- ...then advances @watermark to @to only after a successful MERGE.
