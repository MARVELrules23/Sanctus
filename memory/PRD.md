# Sanctus — Catholic Meal Prep & Workout Scheduling

## Vision
Order daily life — food, exercise, and prayer — to the rhythm of the Roman Catholic liturgical calendar.

## Stack
- Expo Router (React Native) frontend
- FastAPI + MongoDB backend
- Claude Sonnet 4.5 via Emergent LLM key for AI meal & workout generation
- Emergent-managed Google Sign-In for auth

## Features
- **Today**: greets the user with the liturgical day (season, feast, abstinence/fast badges), today's devotion, generated meal and workout.
- **Meals**: weekly meal planner. Each day shows breakfast/lunch/dinner crafted by AI with awareness of fasting/abstinence (no meat on Fridays / Lent), festive meals on solemnities. Includes ingredients and reflection.
- **Workouts**: weekly workout planner themed by liturgical season — penitential strength in Lent, joyful cardio in Easter, gentle Sunday rest. Each workout includes opening/closing prayer.
- **Calendar**: monthly liturgical calendar with color-coded day cells, solemnity stars, detail panel showing feast, season, abstinence/fast/Lord's day badges.
- **Profile**: dietary, allergies, fitness level/goal, devotion focus preferences. Sign out.

## Backend Endpoints
- `POST /api/auth/session` — exchange Emergent session_id for app session
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/liturgical/day?date=YYYY-MM-DD`
- `GET /api/liturgical/month?year=Y&month=M`
- `GET /api/preferences` / `PUT /api/preferences`
- `POST /api/meals/generate` / `GET /api/meals?date=` / `GET /api/meals/week?start=`
- `POST /api/workouts/generate` / `GET /api/workouts?date=` / `GET /api/workouts/week?start=`

## Design
Reverent & traditional aesthetic: cream/parchment background, deep stained-gl- Catholic-themed daily devotion + Liturgical calendar
- AI meal planning (Claude Sonnet 4.5) with feast-day-aware ingredients
- AI workout planning with liturgical themes
- Weekly meal & workout planner
- **Live daily Mass readings** (Universalis → USCCB scrape → AI fallback)
- **Rosary timer** with 20 mysteries, full prayer cycle
- **Weekly grocery list** with PDF + native share-sheet export
- **Custom meal/workout plans** — AI-assisted free-form editor
- **Catholic journal** — write, save, and delete entries with movement-of-the-heart mood tags
- Google sign-in via Emergent-managed Auth
- Cream/navy/gold aesthetic, Cormorant Garamond + Lora serifs.
- **Sanctus Library** — curated Catholic books (in-app reader for public-domain classics, plus external links), live Catholic **radio stations** with a persistent global mini-player that follows the user across the entire app, and Catholic **films** delivered as in-app YouTube embeds (Saints / Doctrine / For Kids / Documentary). Admin CRUD for all three media types.



---

## 🗓 Planned feature — Liturgical Challenges (deferred — build later)

**Concept:** Seasonal day-by-day challenge tracks tied to the liturgical calendar. Each active day surfaces a morning prayer + 5 challenges + a "fun fact" steeped in Catholic tradition surrounding the destination feast.

### Three seasonal tracks
| Track | Window | Climax |
|---|---|---|
| Hallowtide Vigil | Oct 1 → Nov 2 | All Saints' / All Souls' |
| Advent → Christmas | First Sunday of Advent → Epiphany (Jan 6) | Christmas / Twelve Days |
| Lent → Easter | Ash Wednesday → Easter Sunday | Easter |

### Daily structure
- **Morning prayer** card (top of Home tab when toggle is ON)
- Tap → opens **5 challenges** for the day (mix of prayer, acts of kindness, asceticism)
- Each challenge has its own checkbox + a daily journal box
- **Fun fact** card below morning prayer — Catholic tradition surrounding the destination feast

### Decisions locked in (user confirmation 2026-06)
1. **Build timing:** **Start: July 2026** (confirmed by user — gives ~10-week buffer before Hallowtide kicks off Oct 1).
2. **Content source:** AI-proposed via Claude Sonnet 4.5; user reviews each day's set in an admin screen and approves before they go live. (No raw AI shipped without review.)
3. **Difficulty tracks:** **Three tiers per day** — Beginner / Committed / Devoted. User picks once at season start; can change between seasons.
4. **Journal integration:** Reuse the existing Journal feature. Each challenge-day entry appears in the normal journal feed, **tagged with the season** (`#hallowtide`, `#advent`, `#lent`).
5. **Off-season behavior:** Both cards hide completely. The existing top-of-home card simply moves up to take their place — no countdown, no "coming soon" filler.
6. **Daily Practice tie-in:** ✅ Completing all 5 challenges checks off "Daily Practice" for that day. (Partial completion does not.)

### Architecture sketch (for the future agent)
- New collection `challenge_seasons` — one doc per (track, year) holding metadata (start_date, end_date, climax_feast).
- New collection `challenge_days` — `{season_id, date, fun_fact, tracks: { beginner: [c1..c5], committed: [c1..c5], devoted: [c1..c5] }, status: draft|approved|live}`.
- New collection `challenge_progress` — `{user_id, date, track, completed_ids[], journal_entry_id?}`.
- Settings toggle: `preferences.challenges_enabled: bool`.
- New admin-only screens for content review (`/admin/challenges/...`) — gated by a `user.is_admin` flag.
- New router `/api/challenges/*` for: today, season state, mark complete, list pending review (admin), approve/reject (admin), regenerate via Claude (admin).
- Home-tab integration: if `challenges_enabled` AND season is active → render `ChallengeMorningCard` + `ChallengeFunFactCard` above the current top card. Else, current home layout unchanged.

### Open questions to revisit before build
- Which morning prayer per day? AI-pick from a small library or always the same per-season prayer?
- Should completing the season unlock a small badge/keepsake in profile?
- Do friends see each other's challenge progress in the Parish tab? (Probably opt-in.)

---

## Feature log — 2026-06-19

### Daytime Prayer (Liturgy of the Hours)
- Added the Little Hours (Terce, Sext, None) as a single "Daytime Prayer" Hour (slug `daytime`) in `backend/liturgy_of_hours.py` — public-domain ferial per-annum form, Latin + English, fixed across the week. Hub now: Lauds · Daytime · Vespers · Compline. No new frontend (existing /liturgy hub + reader handle it).

### Virtus (home page — replaced the Journal preview card)
- `backend/virtues.py` (wired with EMERGENT_LLM_KEY). 9 topics: chastity, charity, humility, patience, temperance, fortitude, spiritual-warfare, habits-discipline, saints-of-virtue.
- Content AI-authored by Claude (claude-sonnet-4-5) on first GET, cached in Mongo `virtue_content`. Subsections: what_is, life_stages (singleness/dating/marriage), overcoming_vice, saints[], and Resources (PREMIUM-gated, 402 for free). saints-of-virtue → intro + saints_by_virtue[].
- Virtue Plans (`virtue_plans`): pick virtues + timeframe → AI goals (do/refrain), check-off tracking. FREE.
- Admin (founder) can edit/regenerate any virtue's content (PUT/regenerate/admin endpoints, 403 for non-admin; edit screen at /virtus/edit/[slug]).
- Frontend: /virtus (hub), /virtus/[slug] (detail), /virtus/plan/[id], /virtus/edit/[slug]; home `VirtusHomeCard`.
- Verified: 25/25 backend pytest + all frontend flows (iteration_42).

### Schedule (calendar-linked) — 2026-06-19
- backend/schedule.py (collection `schedule_items`), wired with EMERGENT-free. Items: kind (meal/workout/virtue/challenge/custom), weekly (days_of_week 0=Sun..6=Sat) OR one-off (date), optional 24h time, notify + notif_ids.
- Endpoints: GET /schedule, GET /schedule/day/{date}, GET /schedule/sources (active virtue plans + enrolled challenges), POST/PUT/DELETE /schedule, PUT /schedule/{id}/notif-ids.
- Frontend: /schedule (day-of-week hub), /schedule/edit (kind+source picker, weekly/one-off, 12-hour AM/PM time picker, reminder toggle). Calendar tab shows schedule dots + a per-day Schedule section. Home 'Schedule' quick-tile.
- Reminders: on-device expo-notifications (LOCAL only, no keys). Web = no-op; real reminders require a built iOS/Android app. expo-notifications plugin added to app.json.
- Verified: 24/24 backend pytest + all frontend flows (iteration_43).

### Schedule → Calendar export — 2026-06-19
- backend/schedule.py: items now carry `ics_token`; PUBLIC GET /api/schedule/ics/{token}.ics returns RFC5545 VCALENDAR (RRULE for weekly, single DTSTART for one-off, VALARM). 404 on bad token.
- Frontend src/calendar-export.ts: googleCalUrl() (Google Calendar render link w/ RRULE) + icsLink() (.ics capability URL). Editor 'Add to your calendar' section (export-google / export-ics) shown for saved items.
- Verified iteration_44 (8 new + 24 regression backend, frontend buttons present).

### TODO NEXT — "Español" whole-site Spanish (agreed plan 2Aa/2Ba)
- Not yet started. Large multi-screen i18n effort: build LanguageProvider + EN|ES toggle on Home, translate Home → tabs → Schedule → Virtus interface (phased), and generate AI content (virtues, readings, meals) in Spanish when ES selected (per-language cache). To be built as a dedicated pass.

## Session update (June 2026)
- FIXED: Virtue plan delete button — replaced web-broken `Alert.alert` with cross-platform `confirm()` helper in `app/virtus/plan/[id].tsx`.
- Spanish AI content: added `lang_ctx.py` + Accept-Language middleware. Frontend `api.ts` sends `Accept-Language: <lang>`. Virtue content/plan goals cached per-language (`virtue_content.lang`); meals/workouts generated in active language. Verified via curl (EN stays English, ES returns Spanish).
- i18n applied to Virtus hub + Schedule list (home + tabs already done).
- BACKLOG (Spanish strings not yet applied): schedule/edit, calendar tab, profile tab, virtus/[slug] detail. Mass readings remain English (USCCB source). Meals/workouts adopt language at generation time (cached by date, regenerate to switch).

## Session update 2 (June 2026)
- Spanish Mass editions: readings now translated to Spanish on demand (citations preserved, excerpts+reflection translated) and cached in a separate `readings_es` collection to avoid the unique `date` index on `readings`. Verified EN/ES.
- Profile: added a Language (Idioma) setting with EN/Español toggle; profile screen fully translated.
- Schedule editor: fixed delete button (web Alert -> confirm helper) and translated title/save/delete.
- Remaining ES backlog: calendar tab, virtus/[slug] detail, schedule editor field labels/KIND chips.

## Session update 3 (June 2026)
- Mass Readings home card now localized (MASS READINGS/Gospel/1st/Psalm/title via AutoText) — verified ES ("LECTURAS DE LA MISA").
- Calendar month header now translates (split month name into its own AutoText so it isn't skipped by the numeric year) — verified ES ("Junio 2026").
- Italian radio stations seeded on startup: Vatican News — Italiano, Radio Maria Italia, Radio Maria Canada (Italiano, serves Italian-American communities).

## Session update 4 (June 2026)
- Profile: added private **Marital Status** (single/married) & **Vocation** (singleness/religious life/marriage) under a "Your Walk with Christ" section with a 🔒 "Private — only you can see this" exclaimer. Stored in `preferences` (PreferencesPayload). Localized via AutoText.
- **Virtus Challenge Badges** (perseverance, not perfection): `virtues.py` `_compute_badge` counts fully-completed vs fallen days over the elapsed plan. Thresholds per user: Gold ≤ goldMax fallen (7d→2,14d→4,30d→6,60d→7, interpolated), Silver up to half the days, Bronze beyond. Shown as `BadgePill` (plan list) + `PerseveranceBadge` card (plan detail). Backend returns `badge` on each plan.
- **Catholic World Map** (Community → "Catholic World Map"): new `catholic_sites.py` (collection `catholic_sites`) seeds 28 curated, accurate sites (churches/basilicas/shrines/apparitions/monasteries) with coords, history, relics[], saints[], miracles[]. GET `/api/sites`, GET `/api/sites/{id}`, localized via translation cache. Frontend uses Leaflet+OpenStreetMap (no API key) inside a WebView (native) / iframe (web) — platform-split `CatholicMapView`. Marker tap → detail bottom-sheet (history, relics, saints, miracles, Learn more). List-view toggle + colored legend. Verified map render + detail on web preview.

## Session update 5 (June 2026)
- **World Map expanded**: catholic_sites.py now seeds 78 curated, accurate sites across 55 countries (all continents) — added e.g. Luján, St Joseph's Oratory, Las Lajas, El Cobre, Esquipulas, Montserrat, Pilar-Zaragoza, Rue du Bac, Mont-Saint-Michel, La Salette, Mariazell, Altötting, Einsiedeln, Infant of Prague, Gate of Dawn, Hill of Crosses, House of the Virgin (Ephesus), Our Lady of Lebanon, St Charbel, Sheshan, Myeongdong, Ōura, Madhu, Yamoussoukro (world's largest church), Uganda Martyrs, etc.
- **Vocation companion (NEW)**: vocations.py serves a hand-curated, accurate guide per vocation (singleness/religious life/marriage) × state (discerning/living): morning prayer, selectable saint companions, ideas (Eucharistic adoration, reading), and a NESTED 'traditions to build' box tailored to state (family/home traditions for living marriage; religious-life traditions for living religious life; discernment practices for discerners). GET /api/vocation/guide, localized via cache. Prefs gained vocation_state + companion_saint. Home shows VocationHomeCard ONLY when a vocation is chosen (clickable → /vocation). Profile gained a discerning/living toggle. Verified iteration_63 (10/10 backend + frontend flows).

## Session update 6 (June 2026)
- **Vocation traditions expanded**: each vocation × state now has richer hand-curated traditions (e.g. marriage-living=11: home altar, Epiphany door-chalking, Angelus, holy water, Sunday feast, renew vows, etc.; religious-life & singleness similarly expanded for both discerning/living). All localized.
- **World Map → 99 sites / 59 countries**, including 6 "churches under persecution" (Baghdad Our Lady of Salvation, Qaraqosh Al-Tahira, Maaloula St Thecla, Owo Nigeria, Managua Nicaragua, Lahore Pakistan). New backend fields persecuted + persecution_note (localized). Highlighted in UI: red map marker (mapHtml .pin.persecuted), red list-row alert icon, "Under persecution" legend entry, and a red "Church under persecution" banner (testID map-persecution-banner) in the detail sheet. Verified iteration_64 (13/13 backend + frontend).

## Session update 7 (June 2026)
- **World Map → 133 sites / 62 countries**: added famous relic/pilgrimage churches — St Nicholas (Bari), Turin (Shroud), Naples (San Gennaro blood), Orvieto (Bolsena corporal), Manoppello (Holy Face), St Mark's Venice, St Dominic Bologna, S.M. sopra Minerva (St Catherine of Siena), Divine Mercy Kraków + Wawel, Lisieux, Paray-le-Monial, Nevers (incorrupt Bernadette), Reims, Chartres, Aachen, Trier (Holy Robe), Loreto-style Loyola/Ávila, Bom Jesus Braga, Medjugorje (2024 nihil obstat), Kibeho (Rwanda), Champion WI (only approved US apparition), Carmel Mission, San Thome Chennai (tomb of St Thomas), Santo Niño Cebu, Melbourne, Cap-de-la-Madeleine, Aylesford, Maipú (Chile), San Nicolás (Argentina), etc. Idempotent seeding verified.
- **Companion devotions**: each saint companion in the vocation "choose a companion to walk with" list now carries a `devotions[]` ({title,body}, 2-3 each) — traditions/devotions to grow closer to that specific saint (e.g. St Joseph → Wednesdays, Litany/Chaplet, "Go to Joseph"; St Thérèse → Little Way, Novena of Roses, sacrifice beads). Localized EN/ES/IT; rendered as a "Ways to grow closer to {saint}" block under the selected companion. Verified iteration_65 (9/9 backend + frontend).

## Session update 8 (June 2026)
- **World Map → 270 sites / 84 countries** (added ~150 more cathedrals/basilicas/shrines worldwide across US states, Latin America, all of Europe, Asia/Middle East, Africa, Oceania).
- **"Saint of the place near you" + mini pilgrimage**: new GET /api/sites/nearby?lat&lng (haversine sort; no-coords returns a daily rotating pick). Map screen shows a "Saint of the place near you" card (uses expo-location with permission flow; locate button + Plan). Detail sheet has "Plan a mini pilgrimage". Picking a preset date (Today/Tomorrow/This&Next Sat/Sun) creates a schedule item kind="pilgrimage" (icon footsteps, color #7A5CB0) via POST /api/schedule recurrence="once" — which renders on the existing Calendar. Added "pilgrimage" to schedule KINDS + ScheduleKind type. Verified backend (nearby + schedule create) and UI render.


## Session update 9 (July 2026) — Navigation, Mass, Community & Bookmarks
- **Journal delete fix**: web-safe `confirmAction` (src/confirm.ts) wired into journal.tsx + journal-list.tsx (Alert.alert was a no-op on RN Web). Verified (iter 76).
- **Liturgy of the Hours moved** from the Bible hub into the **Prayer hub** (prayer-card-liturgy → /liturgy). Removed bible-liturgy-link.
- **Mass tab (NEW)**: Home 'Grocery' quick-tile replaced with a **Mass** tile → new `/mass` hub. Hub cards: Today's Mass Readings (→/readings), Mass Missals (→/missals, moved out of Bible hub), Find a Mass Near You (→/churches). Grocery still lives inside Meals.
- **Fully readable daily readings**: usccb.py now returns `*_full` fields (full scripture text from Universalis for today); server.py caches + translates them (es/it); /readings renders full text (falls back to excerpt for past dates/other sources). (iter 77)
- **Community Prayer Journal (NEW)**: collections `community_prayers` + `community_prayer_prays`. Endpoints GET/POST /api/community/prayers, POST /api/community/prayers/{id}/pray (toggle), DELETE. Screen /community/prayers (composer + anonymous toggle + 'I prayed' + delete-own). Banner on Community tab. (iter 78)
- **Friends list on Profile**: Profile 'Friends' section (accepted friends via /community/friends/list) with manage link → /community/people. (iter 78)
- **App-wide Bookmarks (NEW)**: generic `bookmarks` collection (kinds prayer|bible|catechism|book|encyclical). Endpoints GET/POST /api/bookmarks, DELETE /api/bookmarks?kind=&ref_id= (idempotent upsert). App-wide `BookmarksProvider` + reusable `BookmarkButton`. Wired into prayer runner, Bible reader, library book/encyclical detail, and the home Catechism card. Profile shows a **Saved** section that deep-links back. (iter 79)

### BACKLOG (Phase 5 — polish, not yet built)
- Virtues home card "X/Z today" timezone consistency (P2, recurring).
- RN Web deprecation warnings (shadow*, pointerEvents) cleanup (P3).
- Admin miracles: bulk "Approve all complete drafts"; hand-match 15 remaining Saint draft photos.
- Pilgrimage day-before reminder + "mark completed"; surface daily companion's "today's act" on Home; "+ Add to my practices" per tradition; deep-link certain traditions.
- "Remember chant on/off" global pref; "Translation note" line on ES/IT liturgy screens; "Pray now" shortcut on Today.
- Optional bookmark hardening: "see all" when >12 saved; toast on add failure.

## Session update 10 (July 2026) — Home tiles, Companion time prayers, Guardian Angel, new library content (iter 80, all pass)
- **Home tile swap**: Self-Defense is now the large FeatureBox (feature-selfdefense → /self-defense); Schedule is now a QuickTile (quick-schedule → /schedule). Added i18n home.selfDefenseSub (en/es/it).
- **Companion time-of-day prayer**: vocations.py now has morning/afternoon/night prayers per vocation; /api/vocation/guide returns all three; /vocation picks by DEVICE LOCAL TIME (Morning 3–12, Afternoon 12–20, Night 20–3).
- **Guardian Angel Chaplet**: added key `guardian_angel` to src/prayers/chaplets.ts (build fn + CHAPLETS entry + CHAPLET_ORDER after st_michael).
- **Encyclicals (embedded, papal, free)**: added Redemptoris Mater, Marialis Cultus, Rosarium Virginis Mariae, Redemptoris Custos, Patris Corde via `scripts/load_encyclicals.py` (BOOKS + SUMMARY_CHAPTERS). NOTE: no papal encyclical exists specifically on Guardian Angels.
- **Devotional Books (external links, in-app browser)**: NEW `scripts/load_devotional_books.py` upserts 7 type=external books (Guardian Angels: Aquinas Treatise on the Angels, Catholic Encyclopedia, EWTN devotion; Blessed Mother: Glories of Mary, True Devotion to Mary; St Joseph: Life & Glories of St Joseph; Saints: Story of a Soul). Library total now 35 books.


## Session update 11 (July 2026) — Full Catechism of the Catholic Church (iter 81, pass)
- Ingested the COMPLETE CCC (English, Vatican archive) as a single free embedded library book: slug `catechism-of-the-catholic-church`, 374 chapters (Prologue → Parts/Sections/Chapters/Articles → paragraphs 1–2865 + IN BRIEF). tradition `reference`, is_premium False. Script: `scripts/load_catechism_full.py` (scrapes TOC + each leaf page; builds running Part·Section·Chapter·Article breadcrumb as chapter subtitle).
- `library.py _public_book` now honors an explicit `is_premium` bool on the doc (so CCC is free though non-papal). Added TRADITION_LABEL "reference" → "Reference" in library index.
- Reader now has a **Table of Contents picker** (needed for 374 chapters): header `reader-toc` list icon → searchable modal (`reader-toc-search`) listing all chapters (`reader-toc-item-<n>`), jumps to chapter. Also benefits multi-chapter encyclicals.
- Removed the legacy empty placeholder `catechism-catholic-church` (deleted DB doc + removed from library_seed_data.SEED_BOOKS) that caused a duplicate Library card.


## Session update 12 (July 2026) — Eastern Catholic (Byzantine) liturgical calendar (iter 82, pass)
- New `eastern_calendar.py`: Byzantine calendar with two reckonings — "new" (Gregorian/Revised-Julian: fixed feasts on civil dates + Roman/Gregorian Pascha) and "old" (Julian: fixed feasts +13 days + Orthodox/Julian Pascha via Meeus). Covers Pascha, Twelve Great Feasts, moveable cycle (Palm Sunday, Ascension, Pentecost, Great/Holy Week), the four great fasts + weekly Wed/Fri abstinence, and curated commemorations.
- Endpoints: GET /api/eastern/month?year&month&calendar and GET /api/eastern/day?date&calendar (same LiturgicalDay shape as Roman).
- Calendar tab: rite toggle (cal-rite-roman / cal-rite-eastern); when Eastern, a New/Old (Gregorian/Julian) toggle (cal-eastcal-new / cal-eastcal-old). Grid + detail reuse the existing renderer. Roman calendar unchanged.
- Verified: Nativity Dec 25 (new) → Jan 7 (old); Theophany Jan 6 → Jan 19; Pascha 2026 Apr 5 (new) vs Apr 12 (old).

## Session update 13 (July 2026) — Byzantine meat-abstinence correctness (Old/Julian)
- Reworked fasting logic in eastern_calendar.py so abstinence from meat lands on the correct civil days for BOTH new and old calendars:
  - Wrap-safe fixed-fast windows (`_win`) — fixes Nativity Fast crossing the civil-year boundary on the Old calendar (civil Nov 28 → Jan 6 now correctly abstinence).
  - Meat abstained daily during Great Lent + Holy Week + Cheesefare week; Nativity, Dormition, and Apostles' Fasts; weekly Wed/Fri year-round.
  - Fast-free periods lift the weekly Wed/Fri rule: Bright Week, week after Pentecost, Publican & Pharisee week, and the Nativity→Theophany-eve afterfeast.
  - Strict fast days always abstain: Exaltation of the Cross (Sep 14), Beheading of the Forerunner (Aug 29), Theophany Eve (Jan 5) — all +13-shifted on the Old calendar.
  - Great feasts lift only the weekly Wed/Fri rule, not the seasonal meat fasts.
- Verified directly across edge cases (old Nativity fast Jan 1–6, afterfeast fast-free Jan 7–17, Theophany eve strict, Bright Week, ordinary Thursdays).

## Session update 14 (July 2026) — Church finder: Catholic-only (in communion with Rome)
- New shared `catholic_filter.py`: allowlist (roman/greek/ukrainian/melkite/maronite/chaldean/coptic/armenian/syriac catholic, syro-malabar/malankara, ruthenian, ordinariate) + blocklist (old/national/liberal/patriotic/independent/apostolic/reformed "catholic", orthodox, anglican, protestant, lutheran, evangelical).
- churches.py (`/churches/nearby` + `/churches/search`, used by the Church finder section AND the Mass tab): replaced the loose name heuristic (matched any "St."/"Cathedral" → Orthodox/Anglican slipped in) and removed old_catholic; now uses strict `is_catholic_place` (denomination-first, narrow name fallback).
- Map pipeline (catholic_sites.py `/sites/bbox` + `/sites/nearby`) and ingest_osm_churches.py: Overpass query tightened to positive Catholic + Eastern-rite denominations MINUS non-communion bodies; ingest now stores `denomination`.
- Cleaned cached map data: purged 2,578 non-communion entries from `osm_churches` (277,109 → 274,531) by denomination + name signals.
- Verified: /sites/bbox and /churches/nearby around Rome return only Catholic churches (no Orthodox/Anglican/Old-Catholic); unit tests on the filter all pass.


## Session update 15 (July 2026) — Rite badges & Profile rite selection
- `catholic_filter.py`: `RITE_LABELS`/`RITE_KEYS`, `rite_label()`, `rite_from_denomination()` (maps an OSM denomination → rite key: latin/byzantine/maronite/chaldean/syro_malabar/syro_malankara/coptic/armenian/syriac/ordinariate).
- Backend: `User`/`UpdateMeRequest` carry `rite` (validated against RITE_KEYS; "" clears). Church payloads now include `rite` — `churches.py _to_church_dict` (nearby/search, defaults Catholic → "latin"), `server.py _community_to_shape` ("latin"), and `catholic_sites.py /sites/bbox` markers (from stored `denomination`).
- Frontend `src/api.ts`: `RiteKey` type, `RITE_LABELS`, `RITE_OPTIONS`, `riteLabel()`; `User.rite`, `ChurchItem.rite`, `updateMe({rite})`.
- Profile: edit-profile.tsx has a "Rite" chip selector (10 rites + Prefer not to say); profile FaithBioChips shows the chosen rite. churches.tsx church card shows a gold "<Rite> Rite" badge (testID `church-rite-<id>`).
- Verified via curl: nearby returns rite=latin for Rome parishes; PUT /auth/me sets byzantine, rejects invalid (400), clears to null. UI verified: rite selector renders all options.

## Session update 16 (July 2026) — Pre-1966 Traditional Latin (1962) calendar
- New backend module `tridentine_calendar.py` (1962 Missal / 1960 rubrics): seasons (Septuagesima, Lent, Passiontide, Paschaltide, Octave of Pentecost, Time after Epiphany/Pentecost, Advent, Christmastide), Christ the King on LAST SUNDAY OF OCTOBER, Gaudete/Laetare rose, full fixed sanctoral with I/II/III class ranks.
- Endpoints `/api/tridentine/day` and `/api/tridentine/month` (mirrors liturgical/eastern).
- Full pre-conciliar discipline (1917 Code): complete abstinence EVERY Friday (lifted on I class feasts); Lenten weekday fasts (Ash Wed & Lenten Fridays & Good Friday = fast+complete abstinence, other Lenten weekdays = fast+partial); Ember Days (Lent/Whitsun/Sept/Advent — Wed&Sat partial, Fri complete, all fast); Rogation Days (Major Apr 25; Minor Mon–Wed before Ascension) as observances; fasting Vigils (Christmas, Pentecost, Assumption, All Saints = fast+complete abstinence).
- Holy Days of Obligation flagged for Universal 1917 (10) + USA traditional (6) lists via `holy_day_note`.
- Frontend: calendar tab 3-way toggle Roman/Traditional (1962)/Eastern (`cal-rite-tridentine`). LiturgicalDay type extended (is_holy_day, holy_day_note, observance, abstinence_type). Grid shows gold holy-day dot + purple observance dot + star on I-class feasts. Detail card shows observance line, Holy Day of Obligation badge + note, and partial-vs-complete abstinence wording. Existing Liturgical Challenges overlay on this calendar too.
- Verified via curl (Easter 2026 Apr 5; Christ the King Oct 25; Septuagesima Feb 1; Ash Wed Feb 18; Sept Ember Sep 23/25/26; Rogations May 11-13; every-Friday abstinence; Christmas/Assumption holy days) and UI screenshots (toggle, Christ the King, Ember Friday detail with fast+abstinence).

## Session update 17 (July 2026) — Library paywall rule
- `library.py`: new `_is_book_premium(doc)` is the single source of truth. FREE = papal encyclicals (tradition 'papal') + external-link books (type 'external') + the Catechism (slug catechism-of-the-catholic-church / tradition 'reference'). PREMIUM = every embedded full-text book with chapters. Used by both `_public_book.is_premium` and the `/books/{slug}/chapters/{idx}` 402 gate (stored is_premium bool no longer overrides the rule).
- Verified via API: embedded books (Confessions, Orthodoxy, Spiritual Exercises) → is_premium True & 402 for non-premium; external books & all encyclicals & Catechism → is_premium False & 200. Admins bypass as before.

## Session update 18 (July 2026) — Library "Free to read" filter + companion devotionals
- Library (frontend `app/library/index.tsx`): added a Books-tab filter chip row (All books / Free to read, testID `library-book-filter-all|free`) that filters to `!is_premium` books; each free book card now shows a green "Free to read" tag (testID `library-free-tag-<slug>`).
- Companions (backend `companions.py`): added `SAINT_DEVOTIONS` (per-slug recommended devotions for all 21 companions) and `VOCATION_DEVOTIONS` (per vocation|state). `_public` now returns `saint_devotions` and `vocation_devotions`.
- Companion screen (`app/companion/[slug].tsx`): new "Recommended devotionals" section (saint-specific, testID `companion-saint-devotions`) plus a vocation-tailored devotions box (testID `companion-vocation-devotions`). `CompanionDetail` type extended in api.ts.
- Verified: /companions/therese-lisieux returns 4 saint devotions + marriage|discerning vocation devotions; UI screenshots confirm both the library free filter/labels and the companion devotionals render.

## Session update 19 (July 2026) — Phase 1 of big batch (radio title, 4 companions, deep-linked devotionals)
- Radio: `RadioPlayerContext.tsx` now passes `metadata:{title: station name, artist:"Sanctus Catholic Radio"}` to the expo-audio source so the lock screen / media session shows the STATION NAME instead of "frontend" (best validated on a native build).
- New companions added to `companions.py` (COMPANIONS + COMPANION_ORDER + SAINT_DEVOTIONS + DAILY_PRAYERS): St. Augustine (augustine), St. John the Baptist (john-the-baptist), St. James the Less (james-the-less), St. Thomas Aquinas (thomas-aquinas) — each with importance, 4 virtues, 10 daily acts, 4 devotions, morning prayer.
- Deep-linked devotionals: `_devotion_route()` + `_with_routes()` in companions.py attach an in-app `route` to saint & vocation devotions by keyword (rosary→/prayer/rosary, chaplet/divine mercy→/prayer/category/chaplets, consecration/enthronement→/consecration, liturgy of hours→/liturgy, stations→/prayer/category/stations, litany→/prayer/category/litany, marian prayers→/prayer/category/marian, novena→/novenas/<slug>). Frontend `CompanionTradition.route?`; companion screen makes devotion rows Pressable with a chevron when a route exists. Verified via API + screenshot.

### REMAINING in this batch (not yet built) — next phases:
1. Custom Challenges (PER-DAY custom entries): components (abstinence, prayer/devotional, works of charity, adoration, virtue), length 7/14/30/60, start date, show on liturgical calendar. Needs backend user-challenge model + endpoints + calendar overlay + create UI.
2. "Write your own prayer" + "Create your own devotional" (pick saint/angel + own criteria); entry points BOTH in Profile ("My Prayers & Devotionals") and Prayer tab; custom devotional can render companion-style.
3. Mass vestments reference per rite (Roman/TLM/Byzantine) with REAL images (Wikimedia Commons, not AI) + meaning text.
4. TLM (1962) & Byzantine Mass readings — user wants FULL readings text every day (resolve citations via app Bible where possible).

## Session update 20 (July 2026) — Phase 2: Custom (user-created) Challenges
- Backend `custom_challenges.py` (new module, registered in server.py; collection `custom_challenges`): CRUD + per-day items across categories (abstinence/prayer/charity/adoration/virtue/other), length 7/14/30/60 (validated 422), start_date, `completed` map. Endpoints: POST/GET `/api/custom-challenges`, GET `/windows?year=`, GET `/{id}`, POST `/{id}/checkin`, DELETE `/{id}`. `_window()` returns ChallengeWindow shape (challenge_id `custom-<id>`, slug=id).
- Calendar (`app/(tabs)/calendar.tsx`): fetches custom windows + list; custom challenges always overlay the grid (like novena); added a "My Challenges" section with a "New" button (testID `cal-create-challenge`) + tappable tiles; day-detail challenge taps route `custom-` → `/custom-challenges/[id]`.
- New screens: `app/custom-challenges/new.tsx` (title, length chips, date stepper, per-day editor with category chips + "Copy Day N to all") and `app/custom-challenges/[id].tsx` (per-day checkoff via checkin, Today highlight, delete). api.ts: types + createCustomChallenge/listCustomChallenges/listCustomChallengeWindows/getCustomChallenge/checkinCustomChallenge/deleteCustomChallenge + CUSTOM_CHALLENGE_CATEGORIES.
- Verified: curl CRUD/windows/checkin/validation + UI screenshots (create flow, calendar overlay Jul 1-7 + My Challenges tile, detail check-offs & Today highlight).

### STILL REMAINING in batch: (3) "Write your own prayer" + "Create your own devotional" (both Profile + Prayer tab entry points); (4) Mass vestments per rite with real Wikimedia images + meaning; (5) TLM(1962) & Byzantine full daily Mass readings.

## Session update 21 (July 2026) — Phase 3: Personal prayers & devotionals
- Backend `personal.py` (registered in server.py; collections `custom_prayers`, `custom_devotions`): CRUD for user prayers (title+body) and devotionals (saint_name, optional saint_slug, intro, practices[]). Endpoints under `/api/my/prayers` and `/api/my/devotions`.
- Frontend screens: `app/my-devotions/index.tsx` (hub: prayers inline-expand + devotionals list, per-item delete, two create buttons), `new-prayer.tsx`, `new-devotional.tsx` (free-text saint/angel + suggestion chips + practices editor), `[id].tsx` (companion-style devotional detail).
- Entry points BOTH: Profile ("My Prayers & Devotionals" row, testID profile-my-devotions) and Prayer tab (card testID prayer-card-my-devotions).
- api.ts: MyPrayer/MyDevotion types + create/list/get/delete functions.
- BUGFIX: `api()` already JSON.stringifies opts.body; my new POST helpers were double-stringifying (createCustomChallenge, checkinCustomChallenge, createMyPrayer, createMyDevotion) causing 422 on the Save buttons. Fixed to pass raw objects. Verified prayer Save now persists end-to-end via UI (this also fixes the Custom Challenges create/checkin buttons).

## Session update 22 (July 2026) — Phase 4: Mass Vestments reference (real photos)
- Backend `vestments.py` (registered): RITES data for Roman (OF), Traditional Latin (1962, incl. Maniple), Byzantine — each vestment has name + meaning + a Wikipedia article title. Lead photo resolved via MediaWiki ACTION API (`/w/api.php prop=pageimages`) with a compliant User-Agent (the REST summary API returns 403 for generic clients). Cached in `vestment_images`. Endpoint `GET /api/vestments`.
- Frontend `app/vestments.tsx`: rite tabs + cards (real image + name + meaning + CC credit). Entry: Mass hub card (testID `mass-vestments-card`).
- Verified: all 17 vestments resolve real images; UI screenshot shows Amice/Alb photos rendering; rite tabs switch (Byzantine Phelonion etc.).

## Phase 5 (TLM/Byzantine full daily readings) — NOT YET BUILT (needs dedicated session)
- Requires an accurate lectionary dataset: the full 1962 Missal proper Epistle+Gospel for every Sunday/feast (+ ferial fallback repeating the preceding Sunday) AND the Byzantine daily cycle (movable Paschal cycle + fixed Menaion). Full text would resolve citations via the app Bible (TLM) and a reliable Byzantine daily-readings source.
- Deferred to keep accuracy (user's explicit bar) — recommend building as its own focused task.

## Session update 23 (July 2026) — Phase 5: TLM (1962) & Byzantine full daily Mass readings (DONE)
- **TLM (1962):** `tridentine_readings.py` — temporal cycle (Advent→Time after Pentecost) + movable feasts of Our Lord + major fixed feasts, ferias repeat the preceding Sunday's Mass (feria_fallback flag). Full Epistle+Gospel text resolved from the embedded Douay-Rheims Bible (`bible.get_chapter`). Endpoint `GET /api/tridentine/readings?date=`. Screen `app/tlm-readings.tsx`.
- **Byzantine:** `byzantine_readings.py` — Paschal cycle (Pascha→Pentecost named Sundays, 32 Sundays after Pentecost, pre-Lent + Great Lent Sundays) + Great Feasts of the Menaion; weekday fallback to most recent Sunday. Multi-SEGMENT refs handle cross-chapter readings (e.g. Heb 11:33–12:2). Uses `eastern_calendar.pascha_for` and Douay-Rheims text. Endpoint `GET /api/eastern/readings?date=&calendar=new|old`. Screen `app/byzantine-readings.tsx` (renders chapter dividers when a reading spans chapters).
- Mass hub (`app/mass/index.tsx`): two new cards — `mass-tlm-readings-card` → /tlm-readings, `mass-byzantine-readings-card` → /byzantine-readings (both trilingual). api.ts: `getTLMReadings`, `getByzantineReadings` + types.
- Coverage note (user-approved): Byzantine ordinary weekdays fall back to the most recent Sunday (not full weekday-by-weekday lectionary). Both rites display Douay-Rheims English.
- Verified: curl across Sundays/feasts/ferias/Pascha/cross-chapter + screenshots of both screens and the Mass hub cards.


## Session update 24 (July 2026) — "My Vocation Companion" home card + Vocation reading/devotion recommendations (DONE)
- Backend `vocations.py`: added `READINGS` (books + papal encyclicals, each with title/author/kind/note and a Library `slug`) and `DEVOTIONAL_RECS` (prayers/novenas/devotions with in-app `route`) per vocation. Included in `_build_guide` output and translated in `_localize` (note for readings; title+body for recs). All 6 readings & 4 recs per vocation verified.
- api.ts: extended `VocationGuide` with `readings?: VocationReading[]` and `devotional_recs?: VocationDevotionalRec[]` (+ new types).
- Home `VocationHomeCard.tsx` rewritten: shows chosen companion's PHOTO (via `getCompanionImage`), "Walking with {name}", "Click to read more" (→ `/companion/[slug]`), and an "Open my Vocation guide" tile (→ `/vocation`). Header "MY VOCATION COMPANION".
- Vocation page `app/vocation/index.tsx`: new "Recommended reading" section (book/encyclical badge, author, note; tappable rows → `/library/books/[slug]`) and "Prayers, novenas & devotions" section (deep-linked rows → novenas/rosary/consecration/liturgy/marian).
- Encyclical/book slugs map to existing free Library entries (e.g. humanae-vitae, patris-corde, gaudete-et-exsultate, devout-life, story-of-a-soul, true-devotion-mary).
- NOTE: Metro runs in CI mode (no hot reload) — must `supervisorctl restart expo` for frontend changes to bundle. Verified via screenshots: home card (St. Joseph photo) + vocation readings/devotion sections render.

## Session update 25 (July 2026) — Novenas for 4 companions + vocation daily Bible verse (DONE)
- Added 4 authentic novenas in `novenas.py`: st-augustine, st-thomas-aquinas, st-john-baptist, st-james-less (each with intro + traditional main_prayer; AI daily contemplation as usual).
- Wired `novena_slug` into COMPANIONS for augustine, thomas-aquinas, john-the-baptist, james-the-less; added a "Novena to St. Thomas Aquinas" devotion (others already had a Novena devotion). Their companion "Novena to…" devotion now deep-links to /novenas/<slug> via `_devotion_route`/`_with_routes`. Verified all 4 companion endpoints return the route and all 4 novena detail pages resolve.
- Vocation daily Bible verse: added `VOCATION_VERSES` (7 Douay-Rheims verses per vocation) + `_daily_verse()` (deterministic by ordinal date) in `vocations.py`; included as `daily_verse` in guide, text translated in `_localize`. api.ts `VocationGuide.daily_verse` added. New "Verse of the day" card (testID vocation-daily-verse) renders at top of `app/vocation/index.tsx`. Verified card renders (Ecclesiastes 4:9-10 for marriage).

## Session update 26 (July 2026) — Bible translations, Family tab, Feast-day food traditions, Home vocation verse (DONE)
- **Bible translations:** `bible.py` now serves multiple translations (getbible.net). Added embedded full-text **Clementina Vulgata (Latin)** alongside Douay-Rheims; `get_chapter(db, slug, ch, translation)`, `_doc_id` per-translation cache, ES localization only for DR. Endpoint `GET /api/bible/chapter/{book}/{ch}?translation=douayrheims|vulgate`. Chapter screen has a DR / Latin·Vulgate toggle (testID bible-trans-vulgate). Bible index has a "More translations" panel linking out to NABRE (USCCB), RSV-2CE (BibleGateway), Knox (testID bible-ext-translation-{i}).
- **Family tab:** new bottom tab (home icon, tab.family EN/ES/IT) → `app/(tabs)/family.tsx` welcoming hub (NOT "coming soon"; user adding content). Bottom bar now 8 tabs.
- **Feast-day food traditions:** new `food_traditions.py` (12 curated recipes keyed to feasts/seasons + home recipe; localized). Endpoints `/api/food-traditions`, `/api/food-traditions/day?date=` (matches liturgical feast then season), `/api/food-traditions/{slug}`. Meals tab has a "Feast-day food traditions" card (testID meals-food-traditions-card) → `app/food-traditions/index.tsx` list → `[slug].tsx` detail (ingredients + steps).
- **Home vocation card daily verse:** VocationHomeCard now shows guide.daily_verse (testID vocation-card-verse) under the guide tile.
- IMPORTANT: parallel search_replace on the SAME file corrupted server.py once (duplicated tail). Recovered via `git checkout` + sequential re-apply. Never parallelize edits to the same file.

## Session update 27 (July 2026) — Children's books + "For Children" Library section (DONE)
- New `backend/library_children_data.py` with 3 original (copyright-safe) full chapter-by-chapter kids' books, tradition="children": "Bible Stories for Little Souls" (12 ch), "Little Saints for Little Hearts" (9 ch), "The Holy Mass for Little Ones" (8 ch).
- `library.py`: seeds `SEED_BOOKS + CHILDREN_BOOKS`; `_is_book_premium` now returns FREE for tradition=="children" (kids' books free to read). Seeded 3 books on startup (verified free, chapters readable).
- Frontend `app/library/index.tsx`: TRADITION_LABEL children="For Children"; grouped memo splits `children` out of authored; renders a dedicated "For Children" section (testID library-section-children) between Books and Encyclicals. Verified rendering with all 3 books + Free-to-read tags.
- NOTE: children's books are FREE by design choice (family focus); if user wants them Premium, remove the children rule in `_is_book_premium`.

## Session update 28 (July 2026) — Family tab (prayers, reminders, devotional, question, saint spotlight), coloring book, book covers (DONE)
- **Book cover art:** generated 3 illustrated covers via Gemini Nano Banana (gen_family_assets.py), stored on library_books.cover_image; `_public_book` returns cover_image; Library book cards now show the illustration.
- **Coloring:** 6 AI line-art pages seeded into `coloring_pages` (cross, chalice-host, nativity, guardian-angel, holy-spirit-dove, sacred-heart). GET /api/coloring-pages. Screens: app/coloring/index.tsx (grid) + [slug].tsx (freehand SVG PanResponder canvas, palette, undo/clear, progress saved to AsyncStorage, translucent strokes over line-art).
- **Family tab** rebuilt (app/(tabs)/family.tsx): GET /api/family/today returns morning_prayer, night_prayer (parent/child call-response), rotating devotional (deep-linked), daily question, and rotating Saint Spotlight (curated 16-saint pool, tap to expand bio). Localized EN/ES/IT.
- **Reminders:** src/family-notifications.ts uses expo-notifications DAILY triggers at 06:00 & 19:00 device-local time (each user's timezone). Permission flow per contract (settings redirect if blocked). Web = unsupported; only fires on installed build.
- Gotcha fixed: find_one with projection excluding _id returns {} (falsy) — use `is None`.
- Children's books remain FREE.
