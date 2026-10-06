-- Bronze: raw Inside Airbnb listings.csv (San Francisco), one row per listing per scrape.
--
-- Every column stays a string: bronze records what the file said, silver decides
-- what it means. Auto Loader (STREAM read_files) ingests each file once, so a
-- newer snapshot dropped next to the old one is appended, and silver keeps the
-- latest row per listing.
--
-- ${source_path} comes from the pipeline's `configuration` block in
-- resources/pipeline.yml (the stable mechanism; the Beta `parameters` block with
-- `:source_path` syntax is SQL-only and not used here).
--
-- Expectations without an action only count violations in the event log; that
-- is deliberate in bronze, which must never drop what the file contained.
CREATE OR REFRESH STREAMING TABLE bronze_listings (
  CONSTRAINT listing_id_present EXPECT (id IS NOT NULL),
  CONSTRAINT no_rescued_data    EXPECT (_rescued_data IS NULL)
)
COMMENT 'Raw Inside Airbnb listings.csv (San Francisco). All 90 columns as strings plus ingestion metadata. Not a Genie source; feeds silver_listings.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path              AS _source_file,
  _metadata.file_modification_time AS _source_modified_at,
  current_timestamp()              AS _ingested_at
FROM STREAM read_files(
  '${source_path}/listings*.csv',
  format              => 'csv',
  header              => true,
  multiLine           => true,     -- descriptions contain newlines
  escape              => '"',
  inferColumnTypes    => false,
  mode                => 'PERMISSIVE',
  rescuedDataColumn   => '_rescued_data',
  schemaEvolutionMode => 'addNewColumns'
);
