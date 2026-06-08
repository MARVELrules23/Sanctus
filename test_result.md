#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

## Backend test plan (this iteration — new endpoints)

### `/api/readings?date=YYYY-MM-DD` (Daily Mass readings)
- Should authenticate via session cookie.
- For **today's date**, must return `source: "universalis"` with non-empty `gospel` and `first_reading` citations.
- For any date, response includes `liturgical_title`, `usccb_url`, `liturgical{}`, and a short `reflection`.
- For arbitrary past/future date, source may be `usccb` or `ai-fallback`. Should never 5xx.
- Reject invalid date format with 400.
- Second call for same date should be cached (fast).

### `/api/journal` (Catholic journal CRUD)
- `POST /api/journal` with `{date, title?, body, mood?}` creates an entry. Empty body → 400.
- `GET /api/journal` lists entries for the current user, most recent first, `items[]` shape.
- `GET /api/journal?date=YYYY-MM-DD` filters by date.
- `GET /api/journal/{entry_id}` returns one entry, 404 if not owned/missing.
- `PUT /api/journal/{entry_id}` updates body/title/mood; empty body → 400.
- `DELETE /api/journal/{entry_id}` deletes; second delete → 404.
- All endpoints require auth and scope to current user (cannot read another user's entry).

### Existing endpoints (regression smoke)
- `/api/meals/generate`, `/api/meals/save`, `/api/meals/suggest`, `/api/meals/grocery`
- `/api/workouts/generate`, `/api/workouts/save`
- `/api/auth/me`, `/api/liturgical/day`

## Frontend test plan (this iteration)
- Tabs render and navigate.
- Today screen: Mass Readings card shows real citations (Gospel/1st/Psalm); tap → `/readings` detail with USCCB link.
- Today screen: Quick tiles (Rosary, Grocery, Journal) route to correct screens.
- Today screen: Journal card "Write today's entry" → editor saves → returns to home → preview updated.
- Meals tab: "Custom plan" → `/edit-meal`; "Grocery list" → `/grocery`.
- Workouts tab: "Custom plan" → `/edit-workout`; "Rosary" → `/rosary`.
- Grocery screen: PDF and Text share actions both fire without errors.
- Journal list: Add new, edit, delete works. Long-press delete on list also works.

## agent_communication

main_agent: "Added live Mass readings (Universalis JSONP, USCCB scrape fallback, AI citations as last resort), Catholic journal with mood tagging (create/edit/delete + list), wired all previously-orphaned screens (rosary, grocery, edit-meal, edit-workout) into navigation, and added real PDF export for the weekly grocery list via expo-print + expo-sharing. Backend extended with `/api/readings` (uses USCCB scraper module) and `/api/journal` CRUD endpoints. Please run backend tests for the new endpoints and a smoke pass over the existing ones."

main_agent_2026-06-08: "Implemented the latest batch of features. Tab bar now: Today · Meals · Workouts · Wellness · Profile (Calendar hidden from bar, still navigable via Today card). New screens/files:

  Backend (already in place; confirm wired):
  - `/api/wellness/profile` GET/PUT, `/api/wellness/log` GET/POST/DELETE, `/api/wellness/suggest` POST
  - `/api/churches/nearby` GET, `/api/churches/saved` GET, `/api/churches/save` POST, `/api/churches/saved/{id}` DELETE
  - `/api/prayers/examen` GET, `/api/prayers/examination` GET
  - `/api/journal` now supports `kind` (free|examen|examination) and `structured` payload
  - `/api/journal/{id}/confess` POST to mark examination entries as confessed

  Frontend:
  - `/app/frontend/app/(tabs)/wellness.tsx` (new tab): profile (weight/height/target/goal/activity), weight-in logger + sparkline, AI brief via /wellness/suggest
  - `/app/frontend/app/churches.tsx` (new screen): expo-location permission flow (pre-prompt → grant → denied/blocked w/ Open Settings), Nearby/Saved segmented control, star toggling, deep links to Maps/Phone/Website
  - `/app/frontend/app/journal.tsx` updated: mode chips Free|Examen|Confession; Examen renders 5 Ignatian prompts (from /prayers/examen); Confession renders 9-section examination of conscience (from /prayers/examination) with checkbox + private notes; ‘Mark as confessed’ button on examination entries
  - `/app/frontend/app/(tabs)/calendar.tsx`: shows entry dot on days with journal entries; below day detail lists journal entries for that day with tap-to-open; ‘Add note’ button creates a new entry pre-dated to the day
  - `/app/frontend/app/(tabs)/index.tsx`: 2-row Quick tile grid (Rosary/Journal/Grocery, Calendar/Churches/Examen)

  Please test all of: new backend routes (auth required, scoping per-user), and frontend flows for Wellness tab, Churches screen permission flow + save/unsave, Journal mode switching + structured save + mark confessed, Calendar journal-linked notes."


main_agent_phase2_2026-06-08: "Phase 2 (Catholic Bible — Douay-Rheims Challoner) shipped. Backend: new `/app/backend/bible.py` service with the full 73-book Catholic canon (slug + DR-Challoner names + modern abbrs + sections ot/deutero/nt + chapter counts), live text fetched from api.getbible.net 'douayrheims' translation on first read and cached per-chapter in `bible_books` Mongo collection (async lock prevents duplicate fetches). New endpoints: GET /api/bible/books, GET /api/bible/chapter/{slug}/{ch} (includes user highlights), POST/DELETE /api/bible/highlight, GET /api/bible/highlights. Highlight palette restricted to {rose, gold, sage, violet}. Frontend: /bible (book index, search, expand → chapter grid), /bible/[book]/[chapter] (verse reader with gold verse numbers, parchment-tone highlight backgrounds, modal sheet with 4 swatches + remove + 'Journal this verse' deep-link, prev/next chapter pager), Today screen gains a Bible quick tile, Journal screen accepts ?verse_ref + ?verse_text params and pre-fills body with an italicized quote + citation, app/_layout already provides Stack so new screens nest cleanly. Backend tests: 32/32 new Phase-2 tests pass; regressions intact. Verified end-to-end via screenshot harness — book list / chapter open / highlight rose+gold / journal deep-link all green."

main_agent_phase1_2026-06-08: "Phase 1 shipped. Added (1) PUT /api/auth/me to update display name + profile picture (data URI / URL / clear). (2) `goal_mode` parameter on POST /api/meals/generate and POST /api/workouts/generate ('liturgical' | 'goals'); when 'goals', wellness profile (weight/height/target_weight/goal_type/activity_level) is injected into the AI prompt and the system message is augmented to weight macros/intensity toward the user's goals while still honoring abstinence/fasts. Frontend: new /edit-profile screen (avatar picker via expo-image-picker w/ full permission flow, name input + validation, live AuthContext update on save), Edit pencil added to Profile user card, new GoalModeToggle pill rendered on Meals and Workouts headers (persisted in AsyncStorage; 'My goals' shown disabled until wellness profile exists — tapping it routes to Wellness tab). Backend testing complete: 24/24 new Phase-1 tests pass, regression suite 117/118. Verified end-to-end via screenshot harness — name save, image upload via picker, toggle switching, and AI generation with both modes all work."

main_agent_phase3_2026-06-08: "Phase 3 (Community) shipped. NEW BACKEND ENDPOINTS (all require auth, all scoped to current user, all prefixed `/api`):
  - GET  /api/community/topics — returns predefined topic rooms + report reasons
  - GET  /api/community/feed?topic=&before=&limit= — paginated global parish feed or filtered by topic slug (cursor on `created_at` ISO)
  - POST /api/community/posts {body, topic?, image?} — create post, auto-tagged with today's liturgical color & season
  - GET  /api/community/posts/{post_id} — single post detail
  - DELETE /api/community/posts/{post_id} — author-only delete
  - POST /api/community/posts/{post_id}/like — toggle like; returns {liked, like_count}
  - GET  /api/community/posts/{post_id}/replies — list replies
  - POST /api/community/posts/{post_id}/replies {body} — add reply
  - DELETE /api/community/replies/{reply_id} — author-only delete
  - GET  /api/community/users/search?q=&limit= — case-insensitive search on name/email
  - GET  /api/community/users/recommended — recently-active posters, fallback to newest users
  - GET  /api/community/users/{user_id} — public profile + recent posts
  - GET  /api/community/dm/threads — inbox with unread counts
  - POST /api/community/dm/threads {user_id} — open/start 1-on-1 thread (deterministic thread_id from sorted user IDs)
  - GET  /api/community/dm/threads/{thread_id}/messages — fetch + mark as read
  - POST /api/community/dm/threads/{thread_id}/messages {body} — send message
  - POST /api/community/report {target_type, target_id, reason, detail?} — report content/users; reasons validated against fixed list
  - POST /api/community/block/{user_id} — block; blocked pair cannot DM
  - DELETE /api/community/block/{user_id} — unblock
New MongoDB collections (indexes created on startup): community_posts, community_post_likes, community_replies, community_dm_threads, community_dm_messages, community_reports, community_blocks.
FRONTEND: new tab `Parish` (6 tabs now) at /app/frontend/app/(tabs)/community.tsx — feed with horizontal topic chips, FAB compose modal with topic picker, optimistic likes, action menu (delete-own / report-others / DM-author), liturgical color rail on each post card. Sub-screens at /app/frontend/app/community/{post/[id].tsx, people.tsx, dm/index.tsx, dm/[thread_id].tsx, user/[id].tsx}. People screen has debounced search + recommendations. DM thread polls every 5s for new messages and uses optimistic send. Profile screen shows author's recent posts. Report modal lists fixed reasons + optional 500-char detail. Avatar component (`/app/frontend/src/components/Avatar.tsx`) and timeAgo util (`/app/frontend/src/utils/time-ago.ts`) added.
NEEDS TESTING: backend endpoints (auth, scoping, pagination, like-toggle, thread creation, report validation), and frontend flows (feed→compose→post, topic filtering, post detail→reply, people search & recommend, DM inbox→thread→send/receive, profile, report flow)."
