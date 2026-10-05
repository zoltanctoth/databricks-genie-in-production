-- Gold: one row per review. The summary file has no review text, reviewer or id.
CREATE OR REFRESH MATERIALIZED VIEW fact_review (
  listing_id BIGINT NOT NULL COMMENT 'Listing that was reviewed. Foreign key to dim_listing.',
  review_date DATE NOT NULL COMMENT 'Date the review was posted. Two rows with the same listing and date are two distinct reviews.',
  CONSTRAINT fact_review_listing_fk FOREIGN KEY (listing_id) REFERENCES dim_listing(listing_id) RELY
)
COMMENT 'One row per guest review of a San Francisco listing, from 2009 to the snapshot date. Contains dates only, no text. Use for review volume over time; join to dim_listing on listing_id.'
TBLPROPERTIES ('quality' = 'gold')
AS
SELECT listing_id, review_date
FROM silver_reviews;
