-- Regression tests for the gold tables and metric views, run by the tests job
-- after every pipeline and metric view run (dev in CI, prod after release).
-- Each check is one assert_true(); the first failing check fails the task with
-- its message. Expected values are for the 2026-06-14 San Francisco snapshot.
--
-- {{catalog}} and {{schema}} are job parameters.

USE CATALOG IDENTIFIER({{catalog}});
USE SCHEMA IDENTIFIER({{schema}});

-- Row counts -------------------------------------------------------------------

SELECT assert_true(
  (SELECT COUNT(*) FROM dim_host) >= 3000,
  'dim_host: expected at least 3,000 rows');
SELECT assert_true(
  (SELECT COUNT(*) FROM dim_listing) >= 7000,
  'dim_listing: expected at least 7,000 rows');

-- Referential integrity (the FK constraints are RELY, not enforced) -------------

SELECT assert_true(
  (SELECT COUNT(*) FROM dim_listing l LEFT ANTI JOIN dim_host h USING (host_id)
   WHERE l.host_id IS NOT NULL) = 0,
  'dim_listing: host_id without a dim_host row');
SELECT assert_true(
  (SELECT COUNT(*) FROM fact_calendar c LEFT ANTI JOIN dim_listing l USING (listing_id)) = 0,
  'fact_calendar: listing_id without a dim_listing row');
SELECT assert_true(
  (SELECT COUNT(*) FROM fact_review r LEFT ANTI JOIN dim_listing l USING (listing_id)) = 0,
  'fact_review: listing_id without a dim_listing row');

-- Every gold column has a comment (Genie reads them) ---------------------------

SELECT assert_true(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema = {{schema}}
     AND table_name IN ('dim_host', 'dim_listing', 'fact_calendar', 'fact_review', 'fact_listing_activity')
     AND (comment IS NULL OR trim(comment) = '')) = 0,
  'gold: column without a comment');

-- Metric views -----------------------------------------------------------------

-- MEASURE() must equal the same aggregate written by hand on the gold tables.
SELECT assert_true(
  (SELECT COUNT(*)
   FROM (SELECT neighbourhood, MEASURE(availability_ratio) AS ratio
         FROM availability_metrics GROUP BY neighbourhood) mv
   FULL OUTER JOIN
        (SELECT l.neighbourhood, AVG(CAST(c.is_available AS INT)) AS ratio
         FROM fact_calendar c JOIN dim_listing l USING (listing_id)
         WHERE c.is_available IS NOT NULL
         GROUP BY l.neighbourhood) gold
     USING (neighbourhood)
   WHERE mv.ratio IS NULL OR gold.ratio IS NULL OR abs(mv.ratio - gold.ratio) > 1e-9) = 0,
  'availability_metrics: availability_ratio by neighbourhood differs from gold');
