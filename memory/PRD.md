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
