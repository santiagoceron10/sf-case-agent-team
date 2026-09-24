# Case 00042

**Date Closed:** 2026-06-11

## Issue Reported
User reported that the Stage field on Opportunity reverts to its previous
value a few seconds after every save, even though the save itself appears
to succeed and no error is shown.

## Root Cause
A record-triggered Flow on Opportunity ("Stage Change Notifications") was
configured to run on every update, including updates it made itself. Each
save re-triggered the Flow, which re-evaluated a stale decision branch and
wrote the prior Stage value back — a classic recursive re-fire, not a
validation rule or permission issue.

## Action Taken
Flow admin added an entry-condition guard ("value has changed") to the
trigger so the Flow only fires on the initial user save, not on its own
resulting update. Verified with Field History that three consecutive saves
no longer show a follow-up automated change.

## Resolution Category
Automation Broken — Recursive Flow

## Status
Closed
