-- Silver: one typed row per listing per night, only for listings that exist in
-- silver_listings.
--
-- The semi join is the referential-integrity step: 90 listing ids (32,850 rows)
-- in the 2026 calendar have no row in listings.csv and are dropped here, so
-- every fact_calendar row has a dim_listing row and the foreign key is honest.
-- Compare COUNT(*) of bronze_calendar and silver_calendar to see the drop.
--
-- QUALIFY keeps the latest ingested row per (listing, night) so a newer
-- calendar snapshot replaces, rather than duplicates, the old one.
CREATE OR REFRESH MATERIALIZED VIEW silver_calendar (
  CONSTRAINT calendar_date_present EXPECT (calendar_date IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT availability_known    EXPECT (is_available IS NOT NULL)
)
COMMENT 'Typed Inside Airbnb calendar, one row per listing per night from the scrape date forward (365 nights), restricted to listings present in silver_listings. No price column exists in the 2026 export. Not a Genie source; feeds fact_calendar and fact_listing_activity.'
TBLPROPERTIES ('quality' = 'silver')
AS
WITH typed AS (
  SELECT
    TRY_CAST(listing_id AS BIGINT)                                        AS listing_id,
    TRY_CAST(date AS DATE)                                                AS calendar_date,
    CASE available WHEN 't' THEN true WHEN 'f' THEN false END             AS is_available,
    CAST(TRY_CAST(minimum_nights AS DOUBLE) AS INT)                       AS minimum_nights,
    CAST(TRY_CAST(maximum_nights AS DOUBLE) AS INT)                       AS maximum_nights,
    _ingested_at
  FROM bronze_calendar
)
SELECT listing_id, calendar_date, is_available, minimum_nights, maximum_nights
FROM typed
LEFT SEMI JOIN silver_listings USING (listing_id)
QUALIFY ROW_NUMBER() OVER (PARTITION BY listing_id, calendar_date ORDER BY _ingested_at DESC) = 1;
