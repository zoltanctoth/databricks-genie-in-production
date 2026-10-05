-- Gold: one row per listing per night, looking forward from the scrape date.
-- A night with is_available = false is blocked, not necessarily booked: the
-- file cannot tell a guest booking from a host block.
CREATE OR REFRESH MATERIALIZED VIEW fact_calendar (
  listing_id BIGINT NOT NULL COMMENT 'Listing the night belongs to. Foreign key to dim_listing.',
  calendar_date DATE NOT NULL COMMENT 'The night (check-in date).',
  is_available BOOLEAN COMMENT 'True if the night can be booked. False means blocked: booked by a guest or closed by the host.',
  minimum_nights INT COMMENT 'Minimum stay that applies to a booking starting this night.',
  maximum_nights INT COMMENT 'Maximum stay that applies to a booking starting this night.',
  CONSTRAINT fact_calendar_listing_fk FOREIGN KEY (listing_id) REFERENCES dim_listing(listing_id) RELY
)
COMMENT 'Forward-looking availability calendar, one row per listing per night (365 nights from the scrape date). No price column exists in the 2026 export. Use for open and blocked night questions; join to dim_listing on listing_id.'
TBLPROPERTIES ('quality' = 'gold')
AS
SELECT listing_id, calendar_date, is_available, minimum_nights, maximum_nights
FROM silver_calendar;
