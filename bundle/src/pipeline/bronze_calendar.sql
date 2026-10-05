-- Bronze: raw Inside Airbnb calendar.csv, one row per listing per night for the
-- 365 nights after the scrape (about 2.7 million rows).
-- The 2026 export has no price columns: listing_id, date, available,
-- minimum_nights, maximum_nights only.
CREATE OR REFRESH STREAMING TABLE bronze_calendar (
  CONSTRAINT listing_id_present EXPECT (listing_id IS NOT NULL),
  CONSTRAINT no_rescued_data    EXPECT (_rescued_data IS NULL)
)
COMMENT 'Raw Inside Airbnb calendar.csv (San Francisco): listing_id, date, available, minimum_nights, maximum_nights. All columns as strings plus ingestion metadata. Not a Genie source; feeds silver_calendar.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path              AS _source_file,
  _metadata.file_modification_time AS _source_modified_at,
  current_timestamp()              AS _ingested_at
FROM STREAM read_files(
  '${source_path}/calendar*.csv',
  format              => 'csv',
  header              => true,
  inferColumnTypes    => false,
  mode                => 'PERMISSIVE',
  rescuedDataColumn   => '_rescued_data',
  schemaEvolutionMode => 'addNewColumns'
);
