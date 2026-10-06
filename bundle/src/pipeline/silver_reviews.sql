-- Silver: one typed row per review, only for listings that exist in silver_listings.
--
-- 4,197 rows of the 2026 summary file belong to listings missing from
-- listings.csv; the semi join drops them. After that, COUNT(*) equals the sum of
-- number_of_reviews in silver_listings (434,102), which is the proof that the
-- 8,790 same-day repeats are distinct reviews and must be kept.
--
-- There is no dedupe: the summary file has no review id, so a second
-- reviews.csv snapshot would double every row. Replace the file and run the
-- pipeline with a full refresh of bronze_reviews instead of adding a file.
CREATE OR REFRESH MATERIALIZED VIEW silver_reviews (
  CONSTRAINT review_date_present EXPECT (review_date IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Typed Inside Airbnb summary reviews, one row per review (listing_id, review_date), restricted to listings present in silver_listings. No review text or reviewer. Not a Genie source; feeds fact_review and fact_listing_activity.'
TBLPROPERTIES ('quality' = 'silver')
AS
SELECT listing_id, review_date
FROM (
  SELECT
    TRY_CAST(listing_id AS BIGINT) AS listing_id,
    TRY_CAST(date AS DATE)         AS review_date
  FROM bronze_reviews
)
LEFT SEMI JOIN silver_listings USING (listing_id);
