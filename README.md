# NaijaMeal - Smart Recipe & Meal Planning System

A web-based meal planning application tailored for Nigerian households, built with Flask and PostgreSQL (Supabase) or SQLite for local development.

## Features

- **User Profile Management**: Capture dietary preferences, health constraints, and household sizes.
- **Intelligent Recommendation Engine**: Rule-based constraint filtering that suggests Nigerian dishes based on available kitchen inventory.
- **Inventory Tracker**: Manual stock input for pantry items with dynamic tracking.
- **Automated Grocery List Generator**: Compares weekly meal plans against current stock to output reconciled shopping lists.
- **20+ Nigerian Recipes**: Pre-loaded database including Jollof Rice, Egusi Soup, Pounded Yam, Pepper Soup, and more.

## Technology Stack

- **Backend**: Python 3, Flask
- **Database**: PostgreSQL on Supabase or SQLite locally (via SQLAlchemy)
- **Frontend**: HTML5, Bootstrap 5, Bootstrap Icons
- **Authentication**: Flask-Login with Werkzeug password hashing

## Quick Start (No Coding Required)

### Step 1: Install Python
1. Go to https://python.org/downloads
2. Download Python 3.11 or newer
3. During installation, **check the box "Add Python to PATH"**
4. Click "Install Now"

### Step 2: Open Terminal / Command Prompt
- **Windows**: Press `Win + R`, type `cmd`, press Enter
- **Mac**: Press `Cmd + Space`, type `Terminal`, press Enter

### Step 3: Navigate to Project Folder
```bash
cd nigerian_meal_planner
```
(Use `cd Desktop` first if you saved it on your desktop)

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Run the Application
```bash
python app.py
```

### Step 6: Open in Browser
Go to: **http://127.0.0.1:5000**

For production, set a strong `SECRET_KEY` environment variable before starting the app. The built-in fallback is for local development only.

### Connect to Supabase

1. Create a Supabase project and open **Project Settings > Database**.
2. Copy the direct URI connection string for local development, or the **Session pooler** connection string for Vercel and other serverless deployments.
3. Add it to `.env` as `DATABASE_URL` and replace the password placeholder. The URL must include `sslmode=require`.
4. Start the app. SQLAlchemy creates the tables and seeds the recipe catalog on the first startup.

The backend connects directly to Supabase PostgreSQL through SQLAlchemy; the Supabase URL and publishable key are not needed for this server-rendered Flask application. `SUPABASE_DB_URL` remains supported as a fallback for older deployments.

## Deploy to Vercel

1. Import this repository into Vercel.
2. Set the `SECRET_KEY` environment variable to a long random value.
3. Set `DATABASE_URL` to the Supabase Session pooler PostgreSQL connection string.
4. Deploy with the default project settings. Vercel uses `api/index.py` as the Flask entry point.

SQLite is retained for local development. Vercel's filesystem is temporary, so a hosted PostgreSQL database is required for persistent users, inventory, and meal plans.

## Default Demo Flow

1. **Register** a new account at `/register`
2. **Set your profile** with health conditions (e.g., "diabetes") and allergies (e.g., "groundnuts")
3. **Add inventory** items like Rice, Palm Oil, Chicken, Pepper
4. **View Recommendations** — the engine filters out unsafe recipes and ranks by pantry match
5. **Create a Meal Plan** for the week
6. **Generate Shopping List** — see only what you need to buy

The recipe collection can be searched by name or description, inventory quantities and personal ingredient prices can be edited directly, and shopping lists include estimated purchase totals based on those prices.

## Project Structure

```
nigerian_meal_planner/
├── app.py                 # Main application (models, routes, engine)
├── requirements.txt       # Python dependencies
├── mealplanner.db         # SQLite database (auto-created)
├── templates/
│   ├── base.html          # Main layout
│   ├── index.html         # Landing page
│   ├── login.html         # Login form
│   ├── register.html      # Registration form
│   ├── dashboard.html     # User dashboard
│   ├── profile.html       # Edit profile/preferences
│   ├── inventory.html     # Pantry management
│   ├── recipes.html       # Browse all recipes
│   ├── recipe_detail.html # Single recipe view
│   ├── recommendations.html # Smart recommendations
│   ├── meal_plan.html     # Weekly scheduler
│   └── shopping_list.html # Auto-generated grocery list
└── static/
    ├── css/
    └── js/
```

## How the Recommendation Engine Works

The engine uses a **two-stage deterministic approach**:

### Stage 1: Hard Constraint Filtering
Removes any recipe that violates non-negotiable rules:
- **Calorie limit**: Recipes exceeding user's per-meal calorie cap are excluded
- **Allergies**: Any recipe containing allergen ingredients is excluded
- **Health conditions**: Diabetic users won't see high-carb swallows; hypertensive users see low-sodium options prioritized
- **Dietary preference**: Vegetarian users see only meat-free recipes

### Stage 2: Inventory Match Ranking
Remaining recipes are scored by pantry overlap:
```
match_score = (matched_ingredients / total_recipe_ingredients) × 100
```
Results are sorted by match_score descending.

## Defense Talking Points

1. **Localized Dataset**: Unlike Mealime or MyFitnessPal, this system contains Nigerian staples (Egusi, Ofada, Swallows) with local cost metrics.

2. **Explainable AI**: The recommendation engine uses transparent rule-based logic (not black-box ML), making it reproducible and debuggable.

3. **Integrated Workflow**: Combines inventory tracking, health constraint enforcement, meal scheduling, and shopping list generation in one platform — addressing the fragmentation gap identified in the literature review.

4. **Constraint Safety**: Hard constraints are applied BEFORE ranking, ensuring a user with a groundnut allergy never sees a recipe containing groundnuts, regardless of inventory match.

## Troubleshooting

**Error: "pip is not recognized"**
- Reinstall Python and check "Add Python to PATH"

**Error: "No module named flask"**
- Run `pip install -r requirements.txt` again

**Database issues**
- Delete `mealplanner.db` and restart the app. It will recreate automatically.

**Port already in use**
- Change the last line in `app.py` to: `app.run(debug=True, port=5001)`

## License

Academic Project — For educational purposes only.
