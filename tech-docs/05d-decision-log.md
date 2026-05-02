# Phase 05d — Decision Log: Fusion Weighting

## Goal

Capture the rationale for the 60/40 vision/NLP weighting in a place that
won't disappear from the codebase. This is the kind of context that
otherwise dies with the engineer who chose it.

## Status

This is a **decision log entry**, not a build task. Treat it as
write-once: do not edit without sign-off, do not refactor in routine
PRs.

## Entry

> **2026-05-02 — Vision/NLP weighting set to 60/40**
>
> Per Section 3.9 of the project report. Rationale:
>
> - A photograph is harder to fabricate than a sentence. The vision
>   output most directly answers whether an accessibility feature
>   physically exists.
> - The NLP score at 40% retains enough influence to drag a contribution
>   below the public-display threshold when the two signals disagree
>   strongly — e.g. a clear photo of a ramp paired with sarcastic text
>   ("great ramp, if you enjoy climbing it") should land in `CAVEAT`,
>   not `PUBLIC`.
> - Sweeps of 70/30 and 50/50 during development showed 60/40 gave the
>   best moderator-rated balance between false-positive suppression and
>   contribution acceptance.
>
> **Sign-off:** project lead, vision sub-team, NLP sub-team.
>
> **To revise:** open a PR that updates this entry, attaches new
> moderator-rated evaluation data, and bumps the values in
> `Settings.vision_weight` and `Settings.nlp_weight`. The settings
> invariant (05b) prevents a half-revised change from booting.

## How to use this doc

When fusion behaviour comes up in a review or postmortem:

1. Read this entry first. It is the canonical answer to "why 60/40?".
2. If you are tempted to change the weights without a PR that updates
   this entry, **stop**. The settings invariant will block boot if you
   misalign them; this entry exists so you don't try.
3. If you are running a sweep experiment, capture the moderator-rated
   results in a new addendum below this entry — do not erase the
   2026-05-02 record.

## Pitfalls / notes

- This file is not generated. Don't add it to a "regenerate docs"
  pipeline; the value comes from being human-curated.
- Future entries go below the existing one in chronological order.
  Never reorder. Newest at the bottom; reading top-to-bottom tells the
  story of how the weighting evolved.
