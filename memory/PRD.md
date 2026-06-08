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
