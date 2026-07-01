# ACLED — inquiry email (send to admin@acleddata.com)

Pedro couldn't find a self-service registration path, so this is a friendly, open-
questions inquiry (not a formal form). Copy-paste, fill the [brackets], send.

---

**To:** admin@acleddata.com
**Subject:** Access inquiry — non-commercial research project (narrative intelligence)

Hi ACLED team,

I'm building a non-commercial research project called **Atlas** that studies how
conflict and crisis narratives propagate across countries and languages — who reports
what, how the framing shifts across borders, and what coverage is missing. I'd like to
use ACLED's conflict-event data as **authoritative reference events** inside the tool:
to show, alongside a news narrative, the real conflict events it relates to (by location
and time), and to link them as context for an analyst.

To be upfront about the use: ACLED events would be **displayed as reference/context** and
used as a **deterministic linking key** (matching events to the news coverage about them).
ACLED data would **not** be used to train or build any machine-learning model, and I would
**attribute ACLED on every surface** per your attribution policy, with the access date.

I wasn't able to find the exact process for this, so a few open questions:

1. What's the right path to request API access for a non-commercial research use like
   this — self-service registration, or does it need a review?
2. Do you need anything from me first — a short project overview, a description of the use
   case, or a call?
3. Are there terms or limits I should be aware of for this kind of use (rate limits,
   attribution, what's permitted vs. not)?

I'm happy to share more detail or a short written overview of the project. Thank you very
much for your time and help.

Best regards,
[Your name]
[Affiliation / role — e.g. "independent researcher" / your org]
[Email / contact]

---

## Notes for Pedro
- **Open questions email** (as you asked) — it introduces the project, states the use
  honestly (the "not for model training" line is the eligibility point ACLED cares about),
  and ASKS about the process rather than assuming a form.
- If they reply pointing to a registration page, the agent already drafted the
  registration-form content + the `ingest_acled.py` fetcher is built and waiting — just
  set `ACLED_USERNAME`/`ACLED_PASSWORD` (or `ACLED_API_KEY`/`ACLED_EMAIL`) as Fly secrets.
- Keep it short — a first inquiry, not the whole pitch. ACLED handles many of these.
