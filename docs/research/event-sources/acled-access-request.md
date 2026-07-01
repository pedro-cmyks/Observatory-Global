# ACLED Access Request — Atlas (narrative-intelligence research)

**Status:** DRAFT, ready to submit. **Date:** 2026-07-01.
**Purpose:** obtain ACLED **API access at the "Research" (non-commercial) level** so
`acled_conflicts_v2` can be populated and conflict EVENTS can bind to Atlas
narrative threads (issue #232). API access is **not** in the free "Open" tier — it
requires registration + the Research access level + accepting the Terms of Use &
Attribution Policy.

> ⚠️ **One decision Pedro must make before submitting** — see "Eligibility &
> honesty note" at the bottom. ACLED's terms prohibit using its data to *train /
> develop an ML/AI system that becomes a substitute for ACLED or exposes ACLED
> data*. Atlas uses ACLED as **displayed reference events + a binding key**, not
> as ML training data — but this must be stated plainly and confirmed acceptable.

---

## 1. Registration (do this first — self-service)

1. Go to the ACLED Access Portal / myACLED registration:
   **https://acleddata.com/register/** (redirects to the current portal;
   fallback: **https://acleddata.com/user/re-activate**).
2. Register with an **institutional / project domain email** if one exists
   (institutional domains confer higher access tiers). If registering as an
   independent researcher, a personal email is accepted but may route to manual
   review.
3. Verify the email, log in, open **"Terms of Use"**, read the Terms of Use &
   Attribution Policy, and **check the acceptance box** at the bottom — you cannot
   generate an access key or be assigned an access level until you accept.
4. In the registration / access form, request the **Research (non-commercial)**
   access level and provide the use-case description below.
5. After acceptance you are assigned an access level and can create API
   credentials (OAuth username/password for the 2026 flow, or a raw key for the
   legacy flow).

### Registration form — ready-to-paste field content

- **Full name:** Pedro Villegas
- **Email:** *(use institutional domain if available; else personal)*
- **Organization / Affiliation:** Atlas — independent narrative-intelligence
  research project (Observatorio Global)
- **Role / Title:** Researcher / Developer
- **Country:** *(your country)*
- **Sector:** Research / Academic (non-commercial)
- **Intended use (short):** Non-commercial research studying how conflict and
  crisis *narratives* propagate across countries and languages. ACLED events would
  be used as displayed, attributed reference events and to precisely connect a
  news article to the real-world event it reports. No resale, no redistribution of
  the ACLED dataset, no use as ML/AI training data.
- **Access level requested:** Research (non-commercial) — includes API access.
- **Attribution commitment:** Yes — ACLED will be attributed per the Attribution
  Policy ("ACLED, accessed on [DATE]. www.acleddata.com.") on every surface and
  export that shows ACLED events, with the applied filters noted.

---

## 2. Email to ACLED (if the form routes to manual review, or to confirm eligibility)

**To:** access@acleddata.com  *(general access questions; use the address shown in
your portal — commercial/licensing questions go to a separate licensing inbox,
which does NOT apply here since this is non-commercial)*
**Subject:** Research (non-commercial) API access request — Atlas narrative-intelligence project

> Dear ACLED Access Team,
>
> I am requesting **API access at the Research (non-commercial) level** for a
> non-commercial research project called **Atlas** (Observatorio Global). I have
> registered a myACLED account and accepted the Terms of Use & Attribution Policy.
>
> **What Atlas is.** Atlas is a narrative-intelligence research system that studies
> **how conflict and crisis narratives propagate across countries and languages** —
> which outlets and publics say what about a given event, how framing differs by
> region, and where coverage is missing. It aggregates open news/text signals
> (GDELT, RSS, Wikipedia, public forums) and clusters them into "narrative threads."
> It is a research project; it is **not a commercial product**, is not sold, and
> serves no advertising.
>
> **How I would use ACLED.** ACLED is the gold-standard conflict-**event** dataset,
> and it fills a specific gap: my current event source (GDELT CAMEO) is
> country-level and text-less, so narrative threads have no *precise* connected
> real-world events. I would use ACLED events in two ways, both fully attributed:
> (1) as **displayed reference events** on a map/timeline alongside a thread
> (event type, actors, location, fatalities, date, source), and (2) to **connect a
> news article to the event it reports** — an ACLED event's `source` URL lets me
> link the same article Atlas already ingested to that verified event. ACLED's
> lat/lon and typed actors give a second, geospatial link.
>
> **What I would NOT do.** I would not resell or redistribute the ACLED dataset,
> would not expose bulk ACLED data for download, and would **not use ACLED data to
> train, test, or develop any machine-learning / AI model** or anything that could
> act as a substitute for ACLED. Atlas's models operate on news text; ACLED is used
> as attributed reference data and as a linking key, not as a training corpus. I
> would honor the redistribution limits and attribute ACLED on every surface and
> export as "ACLED, accessed on [DATE]. www.acleddata.com.", noting the filters
> applied.
>
> **Technical footprint.** Low volume: a scheduled query for recent events
> (rolling ~3-day window), paginated within your row limits, cached locally — not a
> bulk mirror of the archive.
>
> Could you confirm that this non-commercial research use qualifies for
> Research-level API access, and let me know if anything further is needed from me
> (e.g. a use-case form or an institutional confirmation)? I am happy to provide
> more detail.
>
> Thank you for maintaining ACLED and for supporting research use.
>
> Best regards,
> Pedro Villegas
> Atlas / Observatorio Global
> *(email / contact)*

---

## 3. Eligibility & honesty note (Pedro must confirm before sending)

ACLED's Content Usage / Terms prohibit using the data to **"train, test, develop,
or improve any ML models, LLMs, AI systems … in any way that creates a substitute
for ACLED, allows access to ACLED data,"** across commercial, academic, *and*
experimental use — but explicitly **encourage legitimate academic inquiry** and
permit **internal analysis**.

**Atlas's honest position:** ACLED is used as (a) displayed, attributed reference
events and (b) a deterministic linking key (source_url / lat-lon / actor) between a
news article and the event it reports. This is **internal analysis + attributed
display**, not model training, and Atlas does not expose or redistribute the ACLED
dataset. The e5 embeddings and NLP models Atlas runs operate on **news text**, not
on ACLED records, and ACLED rows are never fed into them as training or fine-tuning
data.

**Decision point for Pedro:** if any future step would embed ACLED `notes`/records
into the vector store or use them to tune a classifier, that likely crosses the
line and would need a different (possibly commercial/licensed) arrangement. Keep
ACLED on the **display + deterministic-bind** side of the line, as the integration
plan specifies. Confirm this framing is acceptable to you before submitting; the
email states it explicitly so ACLED can flag any concern up front.

---

## 4. Access facts (researched 2026-07-01)

| Item | Finding |
|---|---|
| Free non-commercial? | **Yes** for registered Research-level users who accept the Terms & Attribution Policy. Commercial use requires a paid corporate license (not applicable here). |
| API in free tier? | **No** — the free "Open" tier excludes API. API requires the **Research** access level (still free for qualifying non-commercial use). |
| Register at | https://acleddata.com/register/ → myACLED / Access Portal (fallback https://acleddata.com/user/re-activate). Accept Terms to unlock a key. |
| Auth (2026) | OAuth password grant → `POST https://acleddata.com/oauth/token` (username, password, grant_type=password, client_id=acled, scope=authenticated) → bearer access token (24h) + refresh token (14d). |
| Auth (legacy) | `key` + `email` as query params on the read endpoint (being phased out). |
| Read endpoint | `GET https://acleddata.com/api/acled/read?_format=json` + filters. Legacy base `api.acleddata.com/acled/read` is deprecated. |
| Row limit / paging | ~5000 rows/call; paginate with `&page=N` until a short page returns. Filter with `field=value` + `field_where=BETWEEN|LIKE|>|<`. |
| Attribution | Required as a condition of use: `ACLED, accessed on [DATE]. www.acleddata.com.` on every visual/export, with filters applied and access date (data is a weekly-updated "living dataset"). |
| Cost | Research (non-commercial) API access: **free**. Commercial: paid license via ACLED licensing. |

Sources: acleddata.com — getting-started, acled-endpoint, elements-of-the-api,
myacled-faqs, contentusage, attributionpolicy, terms-of-use (fetched 2026-07-01).
