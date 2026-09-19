from app import app, db, Recipe, RecipeIngredient, MealPlanItem


STANDALONE_NAMES = [
    "Eba",
    "Pounded Yam",
    "Semovita",
    "Wheat-meal",
    "Fufu",
    "Amala",
    "Starch",
]

UPDATES = [
    {"old_name": "Akara", "new_name": "Akara with Pap & Milk", "extra_calories": 210},
    {"old_name": "Moi Moi", "new_name": "Moi Moi with Pap & Milk", "extra_calories": 210},
    {"old_name": "Fried Plantain & Egg", "new_name": "Fried Plantain, Egg & Pap", "extra_calories": 210},
    {"old_name": "Egusi Soup", "new_name": "Egusi Soup with Eba", "extra_calories": 300},
    {"old_name": "Ogbono Soup", "new_name": "Ogbono Soup with Pounded Yam", "extra_calories": 350},
    {"old_name": "Oha Soup", "new_name": "Oha Soup with Fufu", "extra_calories": 330},
    {"old_name": "Edikang Ikong", "new_name": "Edikang Ikong with Eba", "extra_calories": 300},
    {"old_name": "Okra Soup (Ila Alasepo)", "new_name": "Okra Soup with Semovita", "extra_calories": 320},
    {"old_name": "Bitterleaf Soup (Ofe Onugbu)", "new_name": "Bitterleaf Soup with Pounded Yam", "extra_calories": 350},
    {"old_name": "Afang Soup", "new_name": "Afang Soup with Fufu", "extra_calories": 330},
    {"old_name": "Ofe Nsala (White Soup)", "new_name": "Ofe Nsala with Pounded Yam", "extra_calories": 350},
    {"old_name": "Banga Soup", "new_name": "Banga Soup with Starch", "extra_calories": 340},
    {"old_name": "Black Soup (Omoebe)", "new_name": "Black Soup with Pounded Yam", "extra_calories": 350},
    {"old_name": "Efo Riro", "new_name": "Efo Riro with Amala", "extra_calories": 320},
    {"old_name": "Fisherman Soup", "new_name": "Fisherman Soup with Fufu", "extra_calories": 330},
    {"old_name": "Omisagwe", "new_name": "Omisagwe (Groundnut Soup) with Fufu", "extra_calories": 330},
    {"old_name": "Vegetable Soup", "new_name": "Vegetable Soup with Wheat-meal", "extra_calories": 310},
]


with app.app_context():
    standalone_matches = Recipe.query.filter(Recipe.name.in_(STANDALONE_NAMES)).all()
    if standalone_matches:
        for recipe in standalone_matches:
            MealPlanItem.query.filter_by(recipe_id=recipe.id).delete()
            RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
            db.session.delete(recipe)
        db.session.commit()
        print(f"Deleted {len(standalone_matches)} standalone recipes.")
    else:
        print("No standalone recipes matched for deletion.")

    updated = 0
    for item in UPDATES:
        recipe = Recipe.query.filter(Recipe.name == item["old_name"]).first()
        if recipe is None:
            continue

        recipe.name = item["new_name"]
        recipe.calories_per_serving += item["extra_calories"]
        updated += 1

    db.session.commit()
    print(f"Updated {updated} recipes with combined meal names.")
