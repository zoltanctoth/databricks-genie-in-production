-- Bronze: raw Inside Airbnb summary reviews, one row per review (438 K rows).
-- Only two columns (listing_id, date); review text is not in the summary file.
-- Error-handling options are explained in bronze_listings.sql.
CREATE OR REFRESH STREAMING TABLE bronze_reviews (
  CONSTRAINT listing_id_present EXPECT (listing_id IS NOT NULL),
  CONSTRAINT no_rescued_data    EXPECT (_rescued_data IS NULL)
)
COMMENT 'Raw Inside Airbnb summary reviews.csv (San Francisco): listing_id, date. All columns as strings plus ingestion metadata. Not a Genie source; feeds fact_review.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path              AS _source_file,
  _metadata.file_modification_time AS _source_modified_at,
  current_timestamp()              AS _ingested_at
FROM STREAM read_files(
  '${source_path}/reviews*.csv',
  format              => 'csv',
  header              => true,
  inferColumnTypes    => false,
  mode                => 'PERMISSIVE',
  rescuedDataColumn   => '_rescued_data',
  schemaEvolutionMode => 'addNewColumns'
);
