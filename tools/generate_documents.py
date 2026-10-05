"""Generate the PDF document set that Genie Agent B reads from a Unity Catalog volume.

Runs locally (no Databricks compute involved). It reads the three Inside Airbnb
San Francisco CSV files, computes the figures with pandas, renders PDFs with fpdf2
and matplotlib, and writes them to an output folder. A separate `aws s3 sync`
mirrors that folder next to the CSVs so the workspace setup notebook can copy it
into a volume.

Document families (32 files by default):

  market_report_<neighbourhood>_<snapshot>.pdf   top 10 neighbourhoods by listing count
  house_rules_<host>_<host_id>.pdf               top 20 hosts by listing count (rules are synthetic)
  sf_short_term_rental_regulation_summary.pdf    one teaching summary of the city rules
  airbnb_sf_data_dictionary.pdf                  one dictionary of the source files and course metrics

Every number in the market reports and host sheets is computed from the snapshot,
so a Genie benchmark can cross-check the PDF against the gold tables. The house
rules themselves are synthetic, seeded by host_id so re-runs are stable, and each
sheet says so.

Usage:
  ~/.venv/bin/python tools/generate_documents.py --data <folder with listings.csv calendar.csv reviews.csv> --out build/documents
"""

from __future__ import annotations

import argparse
import io
import random
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import pandas as pd
from fpdf import FPDF
from fpdf.enums import TableCellFillMode, XPos, YPos
from fpdf.fonts import FontFace

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SNAPSHOT = "2026-06-14"
GENERATED_ON = "2026-10-02"
PROJECT = "Databricks Genie in Production"
ATTRIBUTION = (
    f"Data: Inside Airbnb (insideairbnb.com), San Francisco snapshot {SNAPSHOT}, "
    "licensed CC BY 4.0; derived figures were computed for this teaching project."
)
TOP_NEIGHBOURHOODS = 10
TOP_HOSTS = 20

FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"

NEIGHBOURHOOD_NOTES = {
    "Downtown/Civic Center": "Civic, hotel and transit core around Market Street, City Hall and Union Square; "
    "dense hotel-room and serviced-apartment supply and the city's largest listing count.",
    "South of Market": "Former warehouse district south of Market Street, now offices, lofts and new residential "
    "towers; a large share of entire-home listings aimed at business travellers.",
    "Western Addition": "Residential area west of Van Ness that includes Alamo Square, Japantown and the Fillmore; "
    "mostly Victorian housing with a mix of private rooms and whole flats.",
    "Mission": "Dense, walkable neighbourhood known for murals, restaurants and Dolores Park; "
    "a strong private-room market and many long-tenured individual hosts.",
    "Nob Hill": "Hilltop neighbourhood of historic hotels and apartment buildings between Union Square and Russian Hill; "
    "hotel rooms and small entire-home units dominate.",
    "Outer Sunset": "Low-rise residential grid along Ocean Beach on the city's western edge; "
    "a quieter market of single-family homes and in-law units.",
    "Financial District": "Office towers and hotels north of Market Street near the Embarcadero; "
    "a small residential base, so most listings are hotel rooms or serviced apartments.",
    "Castro/Upper Market": "Residential hillside neighbourhood around Castro Street and the upper stretch of Market Street; "
    "Victorian flats, mostly entire-home listings.",
    "North Beach": "Historic Italian neighbourhood between Chinatown and Fisherman's Wharf; "
    "small apartments and boutique hotels close to the tourist waterfront.",
    "Bernal Heights": "Hilly residential neighbourhood south of the Mission with a village-like main street; "
    "owner-occupied homes with in-law units and private rooms.",
}


# --------------------------------------------------------------------------- data


@dataclass
class Data:
    listings: pd.DataFrame
    calendar: pd.DataFrame
    reviews: pd.DataFrame


def classify_license(value: object) -> str:
    """Map the free-text license field onto the city's registration scheme."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "missing"
    text = str(value).strip()
    if re.match(r"^STR-\d+$", text, re.IGNORECASE):
        return "certificate"
    if re.match(r"^\d{4}-\d+STR$", text, re.IGNORECASE):
        return "pending"
    if text.lower().startswith("exempt") or "not needed" in text.lower():
        return "exempt"
    return "other"


def load(data_dir: Path) -> Data:
    listings = pd.read_csv(data_dir / "listings.csv", low_memory=False)
    listings["price_num"] = (
        listings["price"].astype("string").str.replace(r"[$,]", "", regex=True).astype(float)
    )
    listings["license_status"] = listings["license"].map(classify_license)
    listings["is_superhost"] = listings["host_is_superhost"].eq("t")
    listings["is_entire_home"] = listings["room_type"].eq("Entire home/apt")

    calendar = pd.read_csv(data_dir / "calendar.csv", usecols=["listing_id", "date", "available"])
    calendar["booked"] = calendar["available"].eq("f")
    occupancy = calendar.groupby("listing_id")["booked"].mean().rename("occupancy_proxy")
    listings = listings.merge(occupancy, left_on="id", right_index=True, how="left")

    reviews = pd.read_csv(data_dir / "reviews.csv")
    reviews["date"] = pd.to_datetime(reviews["date"])
    return Data(listings, calendar, reviews)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def money(value: float) -> str:
    return "n/a" if pd.isna(value) else f"${value:,.0f}"


def pct(value: float) -> str:
    return "n/a" if pd.isna(value) else f"{value * 100:.1f}%"


# --------------------------------------------------------------------------- pdf base


class Doc(FPDF):
    def __init__(self, title: str, subtitle: str, kind: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_title = title
        self.doc_subtitle = subtitle
        self.doc_kind = kind
        self.add_font("DejaVu", "", FONT_DIR / "DejaVuSans.ttf")
        self.add_font("DejaVu", "B", FONT_DIR / "DejaVuSans-Bold.ttf")
        self.add_font("DejaVu", "I", FONT_DIR / "DejaVuSans-Oblique.ttf")
        self.set_margins(18, 20, 18)
        self.set_auto_page_break(auto=True, margin=22)
        self.set_title(title)
        self.set_author(PROJECT)
        self.set_subject(subtitle)
        self.set_creator("tools/generate_documents.py")
        self.alias_nb_pages()

    def header(self):
        self.set_font("DejaVu", "", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 5, f"{PROJECT}  |  {self.doc_kind}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-18)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(110, 110, 110)
        self.multi_cell(0, 3.6, ATTRIBUTION, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 4, f"Generated {GENERATED_ON}  |  Page {self.page_no()}/{{nb}}", align="R")
        self.set_text_color(0, 0, 0)

    # helpers -------------------------------------------------------------
    def title_block(self):
        self.set_font("DejaVu", "B", 18)
        self.multi_cell(0, 9, self.doc_title, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("DejaVu", "I", 10)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5.5, self.doc_subtitle, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def h2(self, text: str):
        if self.get_y() > self.h - self.b_margin - 40:  # keep headings with their content
            self.add_page()
        self.ln(2)
        self.set_font("DejaVu", "B", 12.5)
        self.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def para(self, text: str, size: float = 9.5, style: str = ""):
        self.set_font("DejaVu", style, size)
        self.multi_cell(0, 5, text, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.5)

    def bullets(self, items: list[str], size: float = 9.5):
        self.set_font("DejaVu", "", size)
        for item in items:
            x = self.get_x()
            self.cell(5, 5, "•")
            self.multi_cell(0, 5, item, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(x)
        self.ln(1.5)

    def callout(self, text: str):
        self.set_fill_color(245, 240, 225)
        self.set_font("DejaVu", "I", 8.8)
        self.multi_cell(0, 4.8, text, align="L", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT, padding=2)
        self.ln(3)

    def simple_table(self, header: list[str], rows: list[list[str]], widths: list[int] | None = None,
                     align: list[str] | None = None):
        self.set_font("DejaVu", "", 9)
        self.set_fill_color(235, 238, 243)
        with self.table(
            borders_layout="HORIZONTAL_LINES",
            cell_fill_color=(248, 249, 251),
            cell_fill_mode=TableCellFillMode.ROWS,
            col_widths=widths,
            text_align=align or ["LEFT"] * len(header),
            line_height=5.5,
            headings_style=FontFace(emphasis="BOLD", fill_color=(220, 225, 235)),
            width=self.epw,
        ) as table:
            head = table.row()
            for h in header:
                head.cell(h)
            for r in rows:
                row = table.row()
                for v in r:
                    row.cell(str(v))
        self.ln(3)

    def chart(self, fig, width: float = 120):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        x = (self.w - width) / 2
        self.image(buf, x=x, w=width)
        self.ln(3)


# --------------------------------------------------------------------------- market reports


def market_reports(data: Data, out: Path) -> list[Path]:
    lst = data.listings
    counts = lst["neighbourhood_cleansed"].value_counts()
    paths = []
    for rank, (hood, n) in enumerate(counts.head(TOP_NEIGHBOURHOODS).items(), start=1):
        sub = lst[lst["neighbourhood_cleansed"] == hood]
        city = lst
        ref = f"SFMR-{SNAPSHOT[:7].replace('-', '')}-{rank:02d}"
        pdf = Doc(
            title=f"{hood}: Short-Term Rental Market Report",
            subtitle=f"San Francisco, Inside Airbnb snapshot {SNAPSHOT}. Report reference {ref}. "
            f"Rank {rank} of {len(counts)} neighbourhoods by listing count.",
            kind="Neighbourhood market report",
        )
        pdf.add_page()
        pdf.title_block()

        pdf.h2("1. Neighbourhood profile")
        pdf.para(NEIGHBOURHOOD_NOTES.get(hood, "San Francisco neighbourhood as defined by the city's analysis boundaries."))

        pdf.h2("2. Key figures")
        kpis = [
            ["Active listings", f"{n:,}", f"{len(city):,}"],
            ["Share of city listings", pct(n / len(city)), "100%"],
            ["Entire home/apt share", pct(sub["is_entire_home"].mean()), pct(city["is_entire_home"].mean())],
            ["Median nightly price (listed)", money(sub["price_num"].median()), money(city["price_num"].median())],
            ["Average nightly price (listed)", money(sub["price_num"].mean()), money(city["price_num"].mean())],
            ["Occupancy proxy, next 365 nights", pct(sub["occupancy_proxy"].mean()), pct(city["occupancy_proxy"].mean())],
            ["Average review score", f"{sub['review_scores_rating'].mean():.2f}", f"{city['review_scores_rating'].mean():.2f}"],
            ["Superhost share", pct(sub["is_superhost"].mean()), pct(city["is_superhost"].mean())],
            ["Listings with a registration certificate", pct(sub["license_status"].eq("certificate").mean()),
             pct(city["license_status"].eq("certificate").mean())],
            ["Listings with no license value", pct(sub["license_status"].eq("missing").mean()),
             pct(city["license_status"].eq("missing").mean())],
        ]
        pdf.simple_table(["Metric", hood, "San Francisco"], kpis, widths=[52, 24, 24], align=["LEFT", "RIGHT", "RIGHT"])

        pdf.h2("3. Room type mix")
        rt = (
            sub.groupby("room_type")
            .agg(listings=("id", "size"), median_price=("price_num", "median"), occupancy=("occupancy_proxy", "mean"))
            .sort_values("listings", ascending=False)
        )
        pdf.simple_table(
            ["Room type", "Listings", "Share", "Median price", "Occupancy proxy"],
            [[k, f"{int(v.listings):,}", pct(v.listings / n), money(v.median_price), pct(v.occupancy)] for k, v in rt.iterrows()],
            widths=[34, 16, 14, 20, 22], align=["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"],
        )
        fig, ax = plt.subplots(figsize=(5.2, 2.6))
        ax.bar(rt.index, rt["median_price"], color="#4a6fa5")
        ax.set_ylabel("Median nightly price (USD)")
        ax.set_title(f"{hood}: median listed price by room type", fontsize=9)
        ax.tick_params(axis="x", labelsize=7)
        ax.tick_params(axis="y", labelsize=7)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        pdf.chart(fig)

        pdf.h2("4. Largest hosts in the neighbourhood")
        hosts = (
            sub.groupby(["host_id", "host_name"])
            .agg(listings=("id", "size"),
                 certificates=("license_status", lambda s: int((s == "certificate").sum())),
                 missing=("license_status", lambda s: int((s == "missing").sum())),
                 superhost=("is_superhost", "max"))
            .sort_values("listings", ascending=False)
            .head(5)
            .reset_index()
        )
        pdf.simple_table(
            ["Host", "Host id", "Listings here", "With certificate", "No license value", "Superhost"],
            [[h.host_name, h.host_id, h.listings, h.certificates, h.missing, "yes" if h.superhost else "no"] for h in hosts.itertuples()],
            widths=[40, 22, 18, 20, 20, 16], align=["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "LEFT"],
        )

        pdf.h2("5. Compliance watch")
        status = sub["license_status"].value_counts()
        long_stay = int(sub["minimum_nights"].ge(30).sum())
        pdf.para(
            f"Of the {n:,} listings, {status.get('certificate', 0):,} display a short-term rental certificate "
            f"(STR- number), {status.get('pending', 0):,} display a pending application record, "
            f"{status.get('exempt', 0):,} claim an exemption, {status.get('other', 0):,} show another value and "
            f"{status.get('missing', 0):,} show no license value at all. "
            f"{long_stay:,} listings require a minimum stay of 30 nights or more and therefore fall outside the "
            f"short-term rental ordinance. See the regulation summary in this document set for what each status means."
        )

        pdf.h2("6. Methodology")
        pdf.bullets([
            "Listed price is the nightly price shown on the listing at scrape time, before fees; listings without a price are excluded from price figures.",
            "Occupancy proxy is the share of the next 365 calendar nights marked unavailable. It mixes bookings with host blocks, so treat it as an upper bound.",
            "Registration status is derived from the free-text license field: STR-nnnnnnn is a certificate, YYYY-nnnnnnSTR is a pending application, 'Exempt' and 'License not needed' are claimed exemptions.",
            "City-wide columns use all 7,332 listings in the snapshot for comparison.",
        ])
        path = out / f"market_report_{slugify(hood)}_{SNAPSHOT[:7]}.pdf"
        pdf.output(str(path))
        paths.append(path)
    return paths


# --------------------------------------------------------------------------- house rules


CHECK_IN = ["3:00 PM", "4:00 PM", "2:00 PM"]
CHECK_OUT = ["10:00 AM", "11:00 AM", "12:00 PM"]
QUIET_HOURS = ["10:00 PM to 8:00 AM", "9:00 PM to 7:00 AM", "11:00 PM to 7:00 AM"]
PETS = ["No pets of any kind", "Dogs under 25 lb allowed with a $75 pet fee per stay", "Pets allowed on request, one per booking"]
SMOKING = ["No smoking or vaping anywhere on the property, including balconies",
           "Smoking only on the outdoor patio; never indoors"]
VISITORS = ["Unregistered visitors are not allowed at any time",
            "Up to two daytime visitors between 9:00 AM and 9:00 PM; no overnight visitors",
            "Visitors allowed if the host is notified in advance"]
EXTRAS = [
    "Shoes off indoors; slippers are provided in the entry closet",
    "Sort recycling, compost and landfill into the three bins under the sink (San Francisco requires it)",
    "Do not move furniture or hang items on the walls",
    "Turn off heating and lights when you leave the unit",
    "Street cleaning days are posted on the fridge; a parking ticket is the guest's responsibility",
    "Report any damage within 24 hours; accidental damage is usually waived if reported promptly",
    "Laundry room is available from 8:00 AM to 8:00 PM",
    "Keep the front gate locked at all times",
]
NOISE_FINE = [150, 200, 250, 300]
PARTY_FINE = [500, 750, 1000]
LATE_CHECKOUT_FEE = [50, 75, 100]


def host_rules(host_id: int, allows_parties: bool) -> dict:
    rng = random.Random(int(host_id))
    rules = {
        "check_in": rng.choice(CHECK_IN),
        "check_out": rng.choice(CHECK_OUT),
        "quiet_hours": rng.choice(QUIET_HOURS),
        "pets": rng.choice(PETS),
        "smoking": rng.choice(SMOKING),
        "visitors": rng.choice(VISITORS),
        "extras": rng.sample(EXTRAS, 3),
        "noise_fine": rng.choice(NOISE_FINE),
        "party_fine": rng.choice(PARTY_FINE),
        "late_fee": rng.choice(LATE_CHECKOUT_FEE),
        "min_age": rng.choice([18, 21, 25]),
        "allows_parties": allows_parties,
    }
    return rules


def house_rules_sheets(data: Data, out: Path) -> list[Path]:
    lst = data.listings
    top = (
        lst.groupby(["host_id", "host_name"]).size().sort_values(ascending=False).head(TOP_HOSTS).reset_index(name="n")
    )
    paths = []
    for rank, host in enumerate(top.itertuples(), start=1):
        sub = lst[lst["host_id"] == host.host_id]
        # Deterministic policy split: roughly one host in four allows small gatherings.
        allows_parties = (rank % 4 == 0)
        rules = host_rules(host.host_id, allows_parties)
        hoods = sub["neighbourhood_cleansed"].value_counts()
        status = sub["license_status"].value_counts()
        years = sub["hosts_time_as_host_years"].dropna()
        superhost = bool(sub["is_superhost"].max())
        ref = f"HR-{host.host_id}"

        pdf = Doc(
            title=f"House Rules: {host.host_name}",
            subtitle=f"Guest policy sheet for all San Francisco listings managed by host {host.host_id}. "
            f"Document reference {ref}. Applies to bookings from {SNAPSHOT} onward.",
            kind="Host house rules",
        )
        pdf.add_page()
        pdf.title_block()
        pdf.callout(
            "Teaching dataset notice: the host name, host id, listing counts and registration figures below come from the "
            f"Inside Airbnb snapshot. The house rules, fees and policies are synthetic, written for the {PROJECT} course, "
            "and do not describe the real host's terms."
        )

        pdf.h2("1. Host profile")
        profile = [
            ["Host name", str(host.host_name)],
            ["Host id", str(host.host_id)],
            ["San Francisco listings in snapshot", f"{host.n:,}"],
            ["Rank among San Francisco hosts", f"{rank} of {lst['host_id'].nunique():,}"],
            ["Entire home/apt listings", f"{int(sub['is_entire_home'].sum()):,}"],
            ["Private or shared rooms", f"{int((~sub['is_entire_home']).sum() - sub['room_type'].eq('Hotel room').sum()):,}"],
            ["Hotel rooms", f"{int(sub['room_type'].eq('Hotel room').sum()):,}"],
            ["Years as a host", f"{years.max():.0f}" if len(years) else "n/a"],
            ["Superhost", "yes" if superhost else "no"],
            ["Median listed nightly price", money(sub["price_num"].median())],
            ["Average review score", f"{sub['review_scores_rating'].mean():.2f}" if sub["review_scores_rating"].notna().any() else "n/a"],
        ]
        pdf.simple_table(["Field", "Value"], profile, widths=[50, 50])

        pdf.h2("2. Neighbourhoods served")
        pdf.simple_table(
            ["Neighbourhood", "Listings", "Share of this host's listings"],
            [[k, f"{v:,}", pct(v / host.n)] for k, v in hoods.head(6).items()],
            widths=[50, 20, 30], align=["LEFT", "RIGHT", "RIGHT"],
        )

        pdf.h2("3. Registration status of this host's listings")
        pdf.simple_table(
            ["Status", "Listings", "Meaning"],
            [
                ["Certificate (STR-nnnnnnn)", status.get("certificate", 0), "Approved short-term rental certificate displayed"],
                ["Pending (YYYY-nnnnnnSTR)", status.get("pending", 0), "Application record displayed while under review"],
                ["Exempt", status.get("exempt", 0), "Listing claims an exemption, for example hotel or 30-night minimum"],
                ["Other value", status.get("other", 0), "Business registration or unrecognised text"],
                ["No value", status.get("missing", 0), "License field empty"],
            ],
            widths=[42, 16, 42], align=["LEFT", "RIGHT", "LEFT"],
        )
        long_stay = int(sub["minimum_nights"].ge(30).sum())
        pdf.para(f"{long_stay:,} of this host's listings require a minimum stay of 30 nights or more.")

        pdf.h2("4. House rules (synthetic)")
        party_line = (
            f"Small gatherings of up to 8 people are allowed until {rules['quiet_hours'].split(' to ')[0]} if the host is told in advance. "
            f"Unannounced parties are charged ${rules['party_fine']:,} and end the stay."
            if rules["allows_parties"]
            else f"Parties and events are not allowed under any circumstances. Violation fee ${rules['party_fine']:,} and immediate end of stay."
        )
        pdf.bullets([
            f"Check-in from {rules['check_in']}; check-out by {rules['check_out']}. Late check-out without approval costs ${rules['late_fee']}.",
            f"Quiet hours are {rules['quiet_hours']}. A documented noise complaint costs ${rules['noise_fine']}.",
            party_line,
            f"{rules['smoking']}.",
            f"{rules['pets']}.",
            f"{rules['visitors']}.",
            f"The person who books must be at least {rules['min_age']} years old and must be present during the stay.",
            "Guests must not exceed the number of people stated in the booking.",
            *[f"{e}." for e in rules["extras"]],
        ])

        pdf.h2("5. Registration and compliance commitments")
        pdf.bullets([
            "Where a listing displays a short-term rental certificate, the host confirms it is the host's permanent residence and that un-hosted stays stay within 90 nights per calendar year.",
            "Listings with a 30-night minimum are rented as intermediate or long-term stays and are not offered for short-term rental.",
            "Guests who notice a listing without a visible certificate or exemption may ask the host for the registration number before booking.",
        ])
        path = out / f"house_rules_{slugify(str(host.host_name))}_{host.host_id}.pdf"
        pdf.output(str(path))
        paths.append(path)
    return paths


# --------------------------------------------------------------------------- regulation summary


def regulation_summary(data: Data, out: Path) -> Path:
    lst = data.listings
    status = lst["license_status"].value_counts()
    pdf = Doc(
        title="San Francisco Short-Term Rental Rules: Teaching Summary",
        subtitle="A plain-language summary of Administrative Code Chapter 41A as published by the Office of Short-Term Rentals, "
        f"checked against sfplanning.org and sf.gov on {GENERATED_ON}, with a mapping to the Inside Airbnb license field. "
        "Not legal advice.",
        kind="Regulation summary",
    )
    pdf.add_page()
    pdf.title_block()
    pdf.callout(
        "This summary was written for a data course. Rules, fees and penalties change; the Office of Short-Term Rentals (OSTR), "
        "shorttermrentals@sfgov.org, 628-652-7599, is the authority. Primary sources: sfplanning.org/str/faqs-short-term-rentals and "
        "sf.gov/guide-opening-short-term-residential-rental."
    )

    pdf.h2("1. Definitions")
    pdf.bullets([
        "A short-term residential rental is a rental of all or part of a home for fewer than 30 nights.",
        "A hosted stay means the host sleeps in the unit during the guest's stay. An un-hosted stay means the host is away.",
        "A Permanent Resident is someone who spends at least 275 nights per calendar year in the unit offered for rental.",
        "Stays of 30 nights or more are not short-term rentals; rent control and tenant protections may apply instead.",
    ])

    pdf.h2("2. Who may host")
    pdf.bullets([
        "Only the Permanent Resident of a unit may offer it, and only that one unit, even in a multi-unit building the host owns.",
        "Tenants may host but may not earn more from short-term rental fees than their monthly rent.",
        "Ineligible: units built without permits, non-residential spaces such as garages or offices, vehicles, tents and sheds, below-market-rate and student housing, and single-room-occupancy units.",
        "Before 2015 all stays under 30 nights were illegal in San Francisco; the current programme dates from that change.",
    ])

    pdf.h2("3. Registration")
    pdf.bullets([
        "Two registrations are required: a Business Registration Certificate from the Treasurer and Tax Collector, and a short-term rental certificate from the OSTR.",
        "The OSTR application fee is $925, non-refundable, and the certificate is valid for two years.",
        "While an application is pending, the listing shows the record number in the form YYYY-nnnnnnSTR (for example 2023-123456STR).",
        "Once approved, the listing must show the certificate number in the form STR-nnnnnnn (for example STR-0001234).",
        "Hosts with approved certificates file quarterly reports of hosted and un-hosted nights.",
        "A listing with an incorrect number can be removed by the platform and pending reservations cancelled.",
    ])

    pdf.h2("4. Night caps")
    pdf.simple_table(
        ["Stay type", "Annual limit", "Condition"],
        [
            ["Hosted", "No limit", "Host is present and sleeps in the unit"],
            ["Un-hosted", "90 nights per calendar year", "Host is away; counts toward the 275-night residency test"],
            ["30 nights or more", "Outside the ordinance", "Treated as a tenancy, not a short-term rental"],
        ],
        widths=[28, 36, 56],
    )

    pdf.h2("5. Enforcement")
    pdf.bullets([
        "Hosting after a denial, suspension or revocation can draw a notice of violation with penalties of $484 per day per unit.",
        "Hosts must cancel pending short stays and remove listings when an application is denied, even during an appeal.",
        "Platforms must verify that a listing carries a valid registration or pending record before accepting bookings.",
        "Hosted and un-hosted offerings must be separate listings with accurate descriptions and photographs.",
    ])

    pdf.h2("6. How the rules appear in the Inside Airbnb data")
    pdf.para(
        "Inside Airbnb scrapes the registration field that platforms display. In the San Francisco snapshot of "
        f"{SNAPSHOT} it contains {len(lst):,} values that fall into five groups:"
    )
    pdf.simple_table(
        ["Status", "Pattern in the license field", "Listings", "Share"],
        [
            ["certificate", "STR-nnnnnnn", f"{status.get('certificate', 0):,}", pct(status.get("certificate", 0) / len(lst))],
            ["pending", "YYYY-nnnnnnSTR", f"{status.get('pending', 0):,}", pct(status.get("pending", 0) / len(lst))],
            ["exempt", "'Exempt' or 'License not needed per OSTR'", f"{status.get('exempt', 0):,}", pct(status.get("exempt", 0) / len(lst))],
            ["other", "Business registration numbers, free text", f"{status.get('other', 0):,}", pct(status.get("other", 0) / len(lst))],
            ["missing", "Empty", f"{status.get('missing', 0):,}", pct(status.get("missing", 0) / len(lst))],
        ],
        widths=[22, 54, 20, 18], align=["LEFT", "LEFT", "RIGHT", "RIGHT"],
    )
    long_stay = int(lst["minimum_nights"].ge(30).sum())
    pdf.para(
        f"{long_stay:,} listings ({pct(long_stay / len(lst))}) require a minimum stay of 30 nights or more. Most of them show "
        "'Exempt' or no value, which is consistent with the ordinance: they are not short-term rentals. Hotel rooms and "
        "licensed tourist hotels are also exempt. A missing value on an entire-home listing with a short minimum stay is the "
        "pattern a compliance analyst would review first."
    )

    pdf.h2("7. Glossary")
    pdf.simple_table(
        ["Term", "Meaning"],
        [
            ["OSTR", "Office of Short-Term Rentals, part of the San Francisco Planning Department"],
            ["TOT", "Transient Occupancy Tax, collected on stays under 30 nights"],
            ["Chapter 41A", "Section of the Administrative Code that contains the short-term rental ordinance"],
            ["Hosting platform", "A website or app such as Airbnb that lists units and takes bookings"],
            ["ILO", "Intermediate Length Occupancy, stays of 30 days to one year, separately permitted"],
        ],
        widths=[28, 92],
    )
    path = out / "sf_short_term_rental_regulation_summary.pdf"
    pdf.output(str(path))
    return path


# --------------------------------------------------------------------------- data dictionary


LISTINGS_COLUMNS = [
    ("id", "Listing identifier. Primary key; joins to calendar.listing_id and reviews.listing_id."),
    ("name", "Listing title written by the host."),
    ("host_id", "Host identifier. One host can have many listings."),
    ("host_name", "Host's public first name or company name."),
    ("hosts_time_as_host_years", "Years since the host account first hosted."),
    ("host_is_superhost", "t or f. Superhost status at scrape time."),
    ("host_identity_verified", "t or f. Whether the platform verified the host's identity."),
    ("neighbourhood_cleansed", "Neighbourhood from the city's analysis boundaries, assigned by coordinates. Use this, not 'neighbourhood'."),
    ("latitude, longitude", "Approximate location, offset by the platform for privacy."),
    ("property_type", "Detailed property description, for example 'Entire rental unit'."),
    ("room_type", "Entire home/apt, Private room, Shared room or Hotel room."),
    ("accommodates", "Maximum number of guests."),
    ("bedrooms, beds, bathrooms_text", "Capacity fields as displayed on the listing."),
    ("amenities", "JSON array of amenity names."),
    ("price", "Nightly listed price in USD as text, for example '$252.00'. Empty when the calendar had no available night."),
    ("minimum_nights", "Minimum stay. 30 or more means the listing is outside the short-term rental ordinance."),
    ("availability_365", "Nights available in the next 365 days at scrape time."),
    ("number_of_reviews", "Reviews received over the listing's lifetime."),
    ("number_of_reviews_ltm", "Reviews in the last twelve months."),
    ("review_scores_rating", "Average overall rating, 0 to 5."),
    ("estimated_occupancy_l365d", "Inside Airbnb's estimate of nights booked in the last 365 days (review-based model)."),
    ("estimated_revenue_l365d", "Inside Airbnb's estimate of revenue in the last 365 days, USD."),
    ("license", "Registration text displayed on the listing. See the regulation summary for the status mapping."),
    ("calculated_host_listings_count", "Number of listings the host has in this city snapshot."),
]
CALENDAR_COLUMNS = [
    ("listing_id", "Foreign key to listings.id."),
    ("date", "Calendar night, 365 nights starting at the scrape date."),
    ("available", "t if the night can be booked, f if booked or blocked by the host."),
    ("minimum_nights, maximum_nights", "Stay limits in force for that night."),
]
REVIEWS_COLUMNS = [
    ("listing_id", "Foreign key to listings.id."),
    ("date", "Date the review was posted. The summary file has no text or reviewer fields."),
]
METRICS = [
    ("Active listings", "Count of listing ids in the snapshot."),
    ("Occupancy proxy", "Share of the next 365 calendar nights with available = f. Mixes bookings and host blocks."),
    ("Booked nights", "Count of calendar nights with available = f."),
    ("Average nightly price", "Mean of price over listings with a price."),
    ("Revenue proxy", "Sum over listings of price times booked nights in the calendar window."),
    ("Average daily rate (ADR)", "Revenue proxy divided by booked nights."),
    ("Superhost share", "Listings whose host is a superhost divided by all listings."),
    ("Licensed share", "Listings whose license field matches STR-nnnnnnn divided by all listings."),
    ("Trailing twelve month reviews", "Reviews dated within the 365 days before the snapshot date."),
    ("Reviews per listing", "Reviews divided by listings over the same dimensions."),
]


def data_dictionary(data: Data, out: Path) -> Path:
    lst, cal, rev = data.listings, data.calendar, data.reviews
    pdf = Doc(
        title="Inside Airbnb San Francisco: Data Dictionary and Metric Glossary",
        subtitle=f"Source files in the snapshot of {SNAPSHOT}, the columns the course uses, and the definitions behind the "
        "metric views and Genie benchmarks.",
        kind="Data dictionary",
    )
    pdf.add_page()
    pdf.title_block()

    pdf.h2("1. Files in the snapshot")
    pdf.simple_table(
        ["File", "Grain", "Rows", "Columns", "Notes"],
        [
            ["listings.csv", "One row per listing", f"{len(lst):,}", "90", "Detailed listings file; host attributes are repeated on every row"],
            ["calendar.csv", "One row per listing per night", f"{len(cal):,}", "5", "365 nights per listing from the scrape date"],
            ["reviews.csv", "One row per review", f"{len(rev):,}", "2", "Summary reviews file: listing id and date only"],
        ],
        widths=[22, 30, 18, 14, 36], align=["LEFT", "LEFT", "RIGHT", "RIGHT", "LEFT"],
    )
    pdf.para(
        f"Reviews span {rev['date'].min():%Y-%m-%d} to {rev['date'].max():%Y-%m-%d}. "
        f"The calendar covers {cal['date'].min()} to {cal['date'].max()}."
    )

    pdf.h2("2. listings.csv columns used in the course")
    pdf.simple_table(["Column", "Definition"], [[c, d] for c, d in LISTINGS_COLUMNS], widths=[40, 80])
    pdf.h2("3. calendar.csv")
    pdf.simple_table(["Column", "Definition"], [[c, d] for c, d in CALENDAR_COLUMNS], widths=[40, 80])
    pdf.h2("4. reviews.csv")
    pdf.simple_table(["Column", "Definition"], [[c, d] for c, d in REVIEWS_COLUMNS], widths=[40, 80])

    pdf.h2("5. Categorical values")
    rt = lst["room_type"].value_counts()
    pdf.simple_table(
        ["room_type", "Listings"], [[k, f"{v:,}"] for k, v in rt.items()], widths=[40, 20], align=["LEFT", "RIGHT"]
    )
    hoods = lst["neighbourhood_cleansed"].value_counts()
    pdf.para(f"neighbourhood_cleansed has {len(hoods)} distinct values. The ten largest:")
    pdf.simple_table(
        ["neighbourhood_cleansed", "Listings"], [[k, f"{v:,}"] for k, v in hoods.head(10).items()],
        widths=[50, 20], align=["LEFT", "RIGHT"],
    )

    pdf.h2("6. Metric glossary")
    pdf.simple_table(["Metric", "Definition"], [[m, d] for m, d in METRICS], widths=[40, 80])

    pdf.h2("7. Known data quality notes")
    pdf.bullets([
        f"{int(lst['price_num'].isna().sum()):,} listings have no price because no night was available at scrape time.",
        f"{int(lst['hosts_time_as_host_years'].isna().sum()):,} listings have no host attributes (host profile unavailable at scrape time).",
        "A handful of listings carry placeholder prices such as $99,999; use medians or trim the top percentile for averages.",
        "Host names are first names or company names and are not unique; always join on host_id.",
        "'neighbourhood' is host-entered free text; 'neighbourhood_cleansed' is the geocoded city boundary and is the field to group by.",
    ])
    path = out / "airbnb_sf_data_dictionary.pdf"
    pdf.output(str(path))
    return path


# --------------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True, help="folder with listings.csv, calendar.csv, reviews.csv")
    ap.add_argument("--out", type=Path, default=Path("build/documents"), help="output folder (emptied first)")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.pdf"):
        stale.unlink()

    data = load(args.data)
    paths = []
    paths += market_reports(data, args.out)
    paths += house_rules_sheets(data, args.out)
    paths.append(regulation_summary(data, args.out))
    paths.append(data_dictionary(data, args.out))

    total = sum(p.stat().st_size for p in paths)
    biggest = max(paths, key=lambda p: p.stat().st_size)
    print(f"{len(paths)} PDFs written to {args.out} ({total / 1024:.0f} KB total, largest {biggest.name} at {biggest.stat().st_size / 1024:.0f} KB)")
    for p in paths:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
