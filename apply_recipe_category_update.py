from app import app, db, Recipe


SIDE_DISH_NAMES = [
    "Eba",
    "Pounded Yam",
    "Semovita",
    "Wheat-meal",
    "Fufu",
    "Amala",
    "Starch",
    "Egusi Soup",
    "Ogbono Soup",
    "Okra Soup (Ila Alasepo)",
    "Afang Soup",
    "Edikang Ikong",
    "Bitterleaf Soup (Ofe Onugbu)",
    "Ofe Nsala (White Soup)",
    "Banga Soup",
    "Black Soup (Omoebe)",
    "Oha Soup",
    "Efo Riro",
    "Fisherman Soup",
    "Omisagwe",
    "Vegetable Soup",
    "Akara",
    "Moi Moi",
    "Fried Plantain & Egg",
]


with app.app_context():
    updated = Recipe.query.filter(
        Recipe.name.in_(SIDE_DISH_NAMES),
        Recipe.category != "Side Dish",
    ).update({"category": "Side Dish"}, synchronize_session=False)
    db.session.commit()
    print(f"Updated {updated} recipes to Side Dish.")