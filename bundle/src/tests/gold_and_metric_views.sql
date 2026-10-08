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
  (SELECT COUNT(*) FROM dim_host) = 3499,
  'dim_host: expected 3,499 rows');
SELECT assert_true(
  (SELECT COUNT(*) FROM dim_listing) = 7332,
  'dim_listing: expected 7,332 rows');
SELECT assert_true(
  (SELECT COUNT(*) FROM fact_calendar) = 2676180,
  'fact_calendar: expected 2,676,180 rows');
SELECT assert_true(
  (SELECT COUNT(*) FROM fact_review) = 434102,
  'fact_review: expected 434,102 rows');
SELECT assert_true(
  (SELECT COUNT(*) FROM fact_listing_activity) = 7332,
  'fact_listing_activity: expected 7,332 rows');

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

-- fact_listing_activity reproduces Inside Airbnb's published estimates ---------

SELECT assert_true(
  (SELECT COUNT(*) FROM fact_listing_activity a JOIN silver_listings s USING (listing_id)
   WHERE a.estimated_nights_l365d <=> s.published_occupancy_l365d) = 7332,
  'fact_listing_activity: estimated_nights_l365d differs from the published occupancy');
SELECT assert_true(
  (SELECT COUNT(*) FROM fact_listing_activity a JOIN silver_listings s USING (listing_id)
   WHERE a.reviews_l30d <=> s.number_of_reviews_l30d
     AND a.reviews_l365d <=> s.number_of_reviews_ltm) = 7332,
  'fact_listing_activity: review windows differ from the listings file');
SELECT assert_true(
  (SELECT COUNT(*) FROM fact_listing_activity a JOIN silver_listings s USING (listing_id)
   WHERE abs(a.estimated_revenue_l365d - s.published_revenue_l365d) > 1) = 0,
  'fact_listing_activity: estimated revenue more than $1 off the published revenue');

-- Metric views -----------------------------------------------------------------

-- MEASURE() must equal the same aggregate written by hand on the gold tables.
SELECT assert_true(
  (SELECT COUNT(*)
   FROM (SELECT neighborhood, MEASURE(availability_ratio) AS ratio
         FROM booking_reference GROUP BY neighborhood) mv
   FULL OUTER JOIN
        (SELECT l.neighbourhood AS neighborhood, AVG(CAST(c.is_available AS INT)) AS ratio
         FROM fact_calendar c JOIN dim_listing l USING (listing_id)
         WHERE c.is_available IS NOT NULL
         GROUP BY l.neighbourhood) gold
     USING (neighborhood)
   WHERE mv.ratio IS NULL OR gold.ratio IS NULL OR abs(mv.ratio - gold.ratio) > 1e-9) = 0,
  'booking_reference: availability_ratio by neighborhood differs from gold');
