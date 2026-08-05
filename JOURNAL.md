## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/80

**Issue title:** DELETE /profiles/{profile_id} doesn't cascade to delete associated reviews and embeddings

**Tier:** [ ] Tier 1  [✓] Tier 2  [ ] Tier 3

**Problem summary:**
When a user deletes a profile via DELETE /profiles/{profile_id}, delete_profile()
only removes the Profile row itself. It does not clean up the reviews rows tied
to that profile in Postgres or the corresponding embeddings stored in the ChromaDB 
vector store. This leaves orphaned reviews and vector embeddings referencing a profile 
ID that no longer exists. Fixing this will make delete_profile() also remove associated 
reviews and their embeddings so no orphaned data remains after deleting a profile.

**Branch name:** fix/80-profile-delete-cascade

**Setup confirmation:** [✓] App runs locally at localhost:5173

**Cohort ledger:** [✓] Issue added to cohort ledger

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/Btran206/pathreview/commit/ebfef1219e169a3dc53726e4341b386e46c1bac6

**Reproduction summary:**
I created a unit test that creates a temporary user profile in CHROMADB and add a dummy memory chunk to it. delete_profile() is then called to see if all the reviews and ingested files were deleted on the postgreSQL side. The test then also checks if any memory chunks were left behind in this case the 0 chunks are expected but 1 chunk remains which proves that this bug exists. 

**PLAN.md link:** https://github.com/Btran206/pathreview/blob/fix/80-profile-delete-cascade/PLAN.md

## Week 9 — Solution building & PR submission

### Check-in 1 (mid-week)

**Skipped**

### Check-in 2 (end of week)

**PR link:** [PR](https://github.com/ascherj/pathreview/pull/861)

**Branch:** `fix/80-cascade-delete-profile-reviews`

**What you built:**
Added `VectorStore.delete_collection()` in `rag/retriever/vector_store.py`, which drops a profile's entire ChromaDB collection and silently no-ops if the collection never existed (e.g. a profile with no ingested sources). Wired it into `delete_profile()` in `core/services/profile_service.py`, calling it after the SQL deletes but before the final `db.commit()`, so a ChromaDB failure rolls back the Postgres deletes instead of leaving the two systems inconsistent.

**Tests added or updated:**
- `tests/unit/test_vector_store.py` (new): unit tests for `delete_collection()` in isolation — deleting an existing collection, deleting a nonexistent one (no-op), and deleting twice (no-op).
- `tests/unit/test_profile_service.py` (new): tests for `delete_profile()`'s Postgres-side cascade and its interaction with `VectorStore` — reviews/sources/profile all get deleted and committed, a not-found profile short-circuits without touching the DB or vector store, a `VectorStore` failure rolls back the transaction, and a documented edge case where a Postgres commit failure *after* a successful vector cleanup can't be undone on the Chroma side.
- `tests/unit/test_profile_delete_vector_cleanup.py` (renamed from `test_profile_delete_cascade.py`, updated): end-to-end tests against a real (tmp-dir-backed) ChromaDB instance confirming `delete_profile()` actually removes the profile's collection — covering a single ingested source, multiple sources sharing one collection, and a profile with no ingested sources.

**Self-review confirmation:** [✓] make check passes  [✓] make test-unit passes

`make test-unit` PR branch: 385 passed vs. main's 375 passed which we added 10 new tests.

`make check` 178 errors on PR branch vs. 182 on main — 4 fewer, all pre-existing issues in files we didn't touch.
Typecheck: 100 errors on PR branch vs. 103 on main — 3 fewer, matching the annotations we added to profile_service.py.

**Draft PR feedback received from:** None
