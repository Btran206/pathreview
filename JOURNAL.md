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

