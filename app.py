from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from urllib.parse import urlparse, parse_qs, quote
from sqlalchemy import inspect, text
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-this-secret')
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
if not database_url:
    if os.environ.get('VERCEL'):
        raise RuntimeError('DATABASE_URL must be configured with a persistent PostgreSQL database on Vercel.')
    database_url = 'sqlite:///mealplanner.db'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
secure_cookies = os.environ.get('SESSION_COOKIE_SECURE', '').lower() in {'1', 'true', 'yes'}
app.config['SESSION_COOKIE_SECURE'] = secure_cookies
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_SECURE'] = secure_cookies


db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

RECIPE_IMAGES = {
    'Jollof Rice': 'jollof-rice.jpeg',
    'Fried Rice': 'fried-rice.jpg',
    'Egusi Soup': 'egusi.jpg',
    'Ogbono Soup': 'ogbono-soup.jpg',
    'Vegetable Soup (Edikaikong)': 'vegetable-soup.jpg',
    'Okra Soup': 'okra-soup.jpg',
    'Banga Soup (Ofe Akwu)': 'banga.jpg',
    'Oha Soup': 'oha-soup.jpg',
    'Pounded Yam': 'pounded-yam.jpg',
    'Eba (Garri)': 'eba.jpg',
    'Semovita': 'semovita.jpg',
    'Amala (Yam Flour)': 'amala.jpg',
    'Wheat Meal': 'wheat-meal.jpg',
    'Moi Moi': 'moi-moi.jpg',
    'Akara': 'Akara.jpg',
    'Pepper Soup': 'pepper-soup.jpeg',
    'Ofada Rice & Stew': 'ofada.jpg',
    'Stew': 'stew.jpg',
    'Beans & Plantain': 'beans-and-plantain.jpg',
    'Yam Porridge (Asaro)': 'yam-porridge.jpg',
    'Coconut Rice': 'coconut-rice.jpg',
}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    household_size = db.Column(db.Integer, default=1)
    health_conditions = db.Column(db.String(300), default='')
    allergies = db.Column(db.String(300), default='')
    dietary_preference = db.Column(db.String(100), default='')
    calorie_limit = db.Column(db.Integer, default=800)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    inventory = db.relationship('Inventory', backref='user', lazy=True, cascade='all, delete-orphan')
    meal_plans = db.relationship('MealPlan', backref='user', lazy=True, cascade='all, delete-orphan')

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, default='')
    instructions = db.Column(db.Text, default='')
    calories_per_serving = db.Column(db.Integer, default=0)
    estimated_cost = db.Column(db.Float, default=0.0)
    prep_time_minutes = db.Column(db.Integer, default=30)
    image_url = db.Column(db.String(300), default='')
    youtube_url = db.Column(db.String(300), default='')
    dietary_tags = db.Column(db.String(200), default='')

    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy=True, cascade='all, delete-orphan')

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), default='')
    unit = db.Column(db.String(20), default='pieces')
    price_per_unit = db.Column(db.Float, default=0.0)

class RecipeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    quantity = db.Column(db.Float, default=1.0)

    ingredient = db.relationship('Ingredient')

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    price_per_unit = db.Column(db.Float, nullable=True)

    ingredient = db.relationship('Ingredient')

class MealPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_start = db.Column(db.Date, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('MealPlanItem', backref='meal_plan', lazy=True, cascade='all, delete-orphan')

class MealPlanItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_plan_id = db.Column(db.Integer, db.ForeignKey('meal_plan.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)
    meal_type = db.Column(db.String(20), default='Dinner')

    recipe = db.relationship('Recipe')


def youtube_embed_url(youtube_url):
    """Return a YouTube embed URL for supported video links."""
    if not youtube_url:
        return None

    parsed = urlparse(youtube_url)
    hostname = parsed.netloc.lower().split(':')[0]
    video_id = None
    if hostname in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [None])[0]
        elif parsed.path.startswith('/embed/'):
            video_id = parsed.path.split('/embed/', 1)[1].split('/', 1)[0]
    elif hostname == 'youtu.be':
        video_id = parsed.path.strip('/').split('/', 1)[0]

    if video_id and len(video_id) == 11:
        return f'https://www.youtube-nocookie.com/embed/{video_id}'
    return None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def seed_database():
    """Populate database with Nigerian recipes and ingredients."""
    if Recipe.query.first():
        return

    ingredient_data = [
        ("Rice", "Grains", "cups"),
        ("Beans", "Grains", "cups"),
        ("Yam", "Tubers", "pieces"),
        ("Plantain", "Fruits", "pieces"),
        ("Garri", "Grains", "cups"),
        ("Semovita", "Grains", "cups"),
        ("Wheat Flour", "Grains", "cups"),
        ("Pounded Yam Flour", "Grains", "cups"),
        ("Vegetable Oil", "Oils", "ml"),
        ("Palm Oil", "Oils", "ml"),
        ("Tomatoes", "Vegetables", "pieces"),
        ("Pepper", "Vegetables", "pieces"),
        ("Onions", "Vegetables", "pieces"),
        ("Spinach", "Vegetables", "bunches"),
        ("Ugu Leaves", "Vegetables", "bunches"),
        ("Bitter Leaf", "Vegetables", "bunches"),
        ("Okra", "Vegetables", "pieces"),
        ("Chicken", "Proteins", "kg"),
        ("Beef", "Proteins", "kg"),
        ("Goat Meat", "Proteins", "kg"),
        ("Fish", "Proteins", "pieces"),
        ("Stockfish", "Proteins", "pieces"),
        ("Crayfish", "Proteins", "cups"),
        ("Egusi Seeds", "Proteins", "cups"),
        ("Ogbono Seeds", "Proteins", "cups"),
        ("Groundnuts", "Proteins", "cups"),
        ("Locust Beans (Iru)", "Condiments", "spoons"),
        ("Seasoning Cubes", "Condiments", "pieces"),
        ("Salt", "Condiments", "spoons"),
        ("Thyme", "Spices", "spoons"),
        ("Curry Powder", "Spices", "spoons"),
        ("Ginger", "Spices", "pieces"),
        ("Garlic", "Spices", "cloves"),
        ("Coconut Milk", "Dairy", "ml"),
        ("Eggs", "Proteins", "pieces"),
        ("Flour", "Baking", "cups"),
        ("Sugar", "Baking", "cups"),
        ("Butter", "Dairy", "spoons"),
        ("Milk", "Dairy", "ml"),
        ("Pepper Soup Spice", "Spices", "spoons"),
        ("Scent Leaf", "Vegetables", "bunches"),
        ("Uziza Leaf", "Vegetables", "bunches"),
        ("Waterleaf", "Vegetables", "bunches"),
        ("Ponmo", "Proteins", "pieces"),
        ("Snail", "Proteins", "pieces"),
        ("Periwinkle", "Proteins", "cups"),
        ("Ofada Rice", "Grains", "cups"),
        ("Palm Nut Extract", "Oils", "cups"),
        ("Cocoyam", "Tubers", "pieces"),
        ("Oha Leaves", "Vegetables", "bunches"),
        ("Carrots", "Vegetables", "pieces"),
        ("Green Peas", "Vegetables", "cups"),
        ("Liver", "Proteins", "kg"),
        ("Shrimp", "Proteins", "kg"),
        ("Yam Flour", "Grains", "cups"),
    ]

    price_by_ingredient = {
        "Rice": 250, "Beans": 300, "Yam": 500, "Plantain": 250,
        "Garri": 150, "Semovita": 200, "Wheat Flour": 220,
        "Pounded Yam Flour": 300, "Yam Flour": 300, "Vegetable Oil": 4,
        "Palm Oil": 5, "Tomatoes": 150, "Pepper": 100, "Onions": 100,
        "Spinach": 200, "Ugu Leaves": 200, "Bitter Leaf": 200,
        "Okra": 100, "Chicken": 3500, "Beef": 4000, "Goat Meat": 4500,
        "Fish": 1800, "Stockfish": 500, "Crayfish": 800,
        "Egusi Seeds": 1200, "Ogbono Seeds": 1300, "Groundnuts": 500,
        "Locust Beans (Iru)": 300, "Seasoning Cubes": 100, "Salt": 50,
        "Thyme": 150, "Curry Powder": 150, "Ginger": 200, "Garlic": 100,
        "Coconut Milk": 8, "Eggs": 250, "Flour": 220, "Sugar": 250,
        "Butter": 200, "Milk": 8, "Pepper Soup Spice": 300,
        "Scent Leaf": 200, "Uziza Leaf": 200, "Waterleaf": 200,
        "Ponmo": 800, "Snail": 2500, "Periwinkle": 1000,
        "Ofada Rice": 400, "Palm Nut Extract": 700, "Cocoyam": 300,
        "Oha Leaves": 250, "Carrots": 150, "Green Peas": 500,
        "Liver": 3500, "Shrimp": 5000,
    }

    ingredient_map = {}
    for name, cat, unit in ingredient_data:
        ing = Ingredient(name=name, category=cat, unit=unit, price_per_unit=price_by_ingredient.get(name, 0))
        db.session.add(ing)
        db.session.flush()
        ingredient_map[name] = ing.id

    recipes = [
        {
            "name": "Jollof Rice",
            "category": "Rice",
            "description": "Classic Nigerian party jollof rice cooked in tomato stew.",
            "instructions": "1. Wash the rice thoroughly and soak it for 15 to 20 minutes so it cooks evenly. 2. Blend the tomatoes, pepper, and onions until smooth; using slightly overripe tomatoes here is a great way to prevent waste. 3. Heat vegetable oil in a large pot and fry the tomato-pepper blend until the raw smell disappears and the sauce thickens. 4. Stir in the chicken, seasoning cubes, thyme, curry powder, and salt, then cook for 3 to 5 minutes. 5. Add the washed rice and enough water to cook it. Cover and cook on low heat. 6. Fluff with a spoon and freeze any leftovers promptly in airtight containers.",
            "calories": 450,
            "cost": 1200,
            "prep_time": 60,
            "dietary_tags": "",
            "ingredients": [("Rice", 3), ("Tomatoes", 5), ("Pepper", 3), ("Onions", 2), ("Vegetable Oil", 100), ("Chicken", 0.5), ("Seasoning Cubes", 2), ("Thyme", 1), ("Curry Powder", 1), ("Salt", 1)]
        },
        {
            "name": "Fried Rice",
            "category": "Rice",
            "description": "Nigerian-style fried rice with mixed vegetables and liver or chicken.",
            "instructions": "1. Parboil the rice until slightly soft, drain, and spread out to cool. Save the starchy rice water to thicken future soups if desired. 2. Heat oil in a pan and fry the onions until translucent. 3. Add carrots, green peas, and any vegetable offcuts you have, stirring briefly. 4. Stir in the liver or chicken, followed by spices and salt. 5. Add the parboiled rice and toss gently until fully coated. 6. Fry on medium heat for a few minutes. Cool completely before transferring leftovers to the fridge to maintain freshness.",
            "calories": 420,
            "cost": 1500,
            "prep_time": 45,
            "dietary_tags": "",
            "ingredients": [("Rice", 3), ("Vegetable Oil", 80), ("Onions", 1), ("Carrots", 2), ("Green Peas", 0.5), ("Liver", 0.3), ("Seasoning Cubes", 2), ("Curry Powder", 1), ("Thyme", 1), ("Salt", 1)]
        },
        {
            "name": "Egusi Soup",
            "category": "Soup",
            "description": "Thick soup made from ground melon seeds, popular across Nigeria.",
            "instructions": "1. Roast or dry the egusi seeds lightly, then grind them into a coarse powder. 2. Heat palm oil in a pot, add the ground egusi, and stir continuously until it thickens. 3. Add chopped onions, pepper, and a little water to loosen the mixture. 4. Add beef, stockfish, crayfish, locust beans, and seasoning, pouring in enough stock to cover. 5. Simmer gently for 15 to 20 minutes. 6. Fold in ugu leaves near the end. Any leftover leafy greens stems can be frozen and used to make vegetable broth later.",
            "calories": 380,
            "cost": 1800,
            "prep_time": 50,
            "dietary_tags": "diabetic-friendly",
            "ingredients": [("Egusi Seeds", 1.5), ("Palm Oil", 100), ("Beef", 0.5), ("Stockfish", 2), ("Crayfish", 0.3), ("Ugu Leaves", 1), ("Onions", 1), ("Pepper", 2), ("Seasoning Cubes", 2), ("Salt", 1), ("Locust Beans (Iru)", 1)]
        },
        {
            "name": "Ogbono Soup",
            "category": "Soup",
            "description": "Draw soup made from wild mango seeds, served with swallow.",
            "instructions": "1. Toast ogbono seeds lightly if needed, then grind into a powder. 2. Heat palm oil in a pot and add the ogbono, stirring continuously. 3. Gradually pour in the meat stock while stirring to prevent lumps. 4. Add beef, goat meat, ponmo, stockfish, crayfish, and seasoning cubes. 5. Simmer until the soup thickens into the classic draw consistency. 6. Add ugu leaves at the end. Store any unused ugu leaves in a damp paper towel in the fridge to keep them crisp for your next meal.",
            "calories": 350,
            "cost": 2000,
            "prep_time": 40,
            "dietary_tags": "diabetic-friendly,low-carb",
            "ingredients": [("Ogbono Seeds", 1), ("Palm Oil", 80), ("Beef", 0.4), ("Goat Meat", 0.3), ("Stockfish", 2), ("Crayfish", 0.3), ("Ugu Leaves", 1), ("Ponmo", 3), ("Seasoning Cubes", 2), ("Salt", 1)]
        },
        {
            "name": "Vegetable Soup (Edikaikong)",
            "category": "Soup",
            "description": "Nutritious soup combining waterleaf and ugu leaves.",
            "instructions": "1. Boil the beef and stockfish until tender and the stock is flavorful. 2. Add palm oil, crayfish, pepper, and onions to build the base. 3. Simmer for a few minutes. 4. Stir in the waterleaf first and cook briefly until it softens. 5. Add ugu leaves last so they stay vibrant, then season with salt and cubes. 6. Simmer for a final 5 minutes. Freeze any excess broth in ice cube trays for easy flavor additions to future dishes.",
            "calories": 280,
            "cost": 1500,
            "prep_time": 45,
            "dietary_tags": "diabetic-friendly,low-sodium",
            "ingredients": [("Waterleaf", 2), ("Ugu Leaves", 2), ("Palm Oil", 60), ("Beef", 0.4), ("Stockfish", 2), ("Crayfish", 0.3), ("Pepper", 2), ("Onions", 1), ("Seasoning Cubes", 1), ("Salt", 0.5)]
        },
        {
            "name": "Okra Soup",
            "category": "Soup",
            "description": "Light soup made with fresh okra and seafood or meat.",
            "instructions": "1. Wash and chop the okra into small pieces. Buy only the okra you need to avoid spoilage; if you have extra, blanch and freeze it immediately. 2. Boil the fish or meat with pepper, onions, and seasoning. 3. Add palm oil and crayfish to create a rich base. 4. Add the chopped okra and simmer briefly, stirring often to prevent it from becoming gummy. 5. Fold in spinach or leafy greens near the end to soften. 6. Taste, adjust salt, and serve immediately.",
            "calories": 220,
            "cost": 1200,
            "prep_time": 30,
            "dietary_tags": "diabetic-friendly,low-carb,low-sodium",
            "ingredients": [("Okra", 10), ("Palm Oil", 40), ("Fish", 2), ("Crayfish", 0.2), ("Pepper", 2), ("Onions", 1), ("Seasoning Cubes", 1), ("Salt", 0.5), ("Spinach", 1)]
        },
        {
            "name": "Banga Soup (Ofe Akwu)",
            "category": "Soup",
            "description": "Palm nut extract soup native to the Niger Delta region.",
            "instructions": "1. Prepare palm nut extract by boiling palm nuts and extracting the liquid, saving the shells to use for compost or fire starters. 2. Bring the extract to a gentle simmer with beef, fish, pepper, and onions. 3. Add crayfish, seasoning cubes, and salt. 4. Stir occasionally so the soup does not stick to the bottom of the pot. 5. Add the scent leaves near the end and cook briefly to release their fragrance. 6. Simmer until thickened to a glossy consistency.",
            "calories": 400,
            "cost": 2000,
            "prep_time": 60,
            "dietary_tags": "",
            "ingredients": [("Palm Nut Extract", 2), ("Beef", 0.4), ("Fish", 2), ("Crayfish", 0.3), ("Scent Leaf", 1), ("Pepper", 3), ("Onions", 1), ("Seasoning Cubes", 2), ("Salt", 1)]
        },
        {
            "name": "Oha Soup",
            "category": "Soup",
            "description": "Traditional Igbo soup made with oha leaves and cocoyam thickener.",
            "instructions": "1. Boil the goat meat or stockfish with onions, pepper, and seasoning until tender. 2. Peel and mash the cocoyam to make a smooth paste. Cocoyam can spoil quickly, so boil and mash any extra to freeze for your next soup. 3. Stir the paste into the stock little by little to thicken. 4. Add palm oil, crayfish, and seasoning, simmering until smooth. 5. Add oha leaves last, stirring gently so they remain bright. 6. Adjust salt and serve hot.",
            "calories": 320,
            "cost": 1800,
            "prep_time": 50,
            "dietary_tags": "diabetic-friendly",
            "ingredients": [("Oha Leaves", 2), ("Cocoyam", 4), ("Palm Oil", 60), ("Goat Meat", 0.4), ("Stockfish", 2), ("Crayfish", 0.3), ("Pepper", 2), ("Seasoning Cubes", 2), ("Salt", 1)]
        },
        {
            "name": "Pounded Yam",
            "category": "Swallow",
            "description": "Smooth yam dough, a staple swallow across Nigeria.",
            "instructions": "1. Peel the yam and cut into chunks. You can use leftover yam peels to start a compost bin if you have a garden space. 2. Boil the yam in salted water until very soft. 3. Transfer to a mortar or food processor. 4. Pound or blend progressively, adding a little water until it turns into a smooth, elastic dough. 5. Knead gently until lump-free. 6. Shape into balls and serve immediately with your stew of choice.",
            "calories": 350,
            "cost": 500,
            "prep_time": 30,
            "dietary_tags": "",
            "ingredients": [("Yam", 1)]
        },
        {
            "name": "Eba (Garri)",
            "category": "Swallow",
            "description": "Cassava granules stirred in hot water to form a firm swallow.",
            "instructions": "1. Bring water to a boil in a pot. 2. Sprinkle in the garri gradually while stirring continuously to prevent lumps. To prevent waste, keep your dry garri tightly sealed in an airtight container to block moisture and pests, ensuring it lasts for months. 3. Keep stirring until the mixture thickens and becomes smooth. 4. Add a little more garri if needed for a firmer texture. 5. Cover for a minute to rest. 6. Stir again and serve warm.",
            "calories": 300,
            "cost": 300,
            "prep_time": 10,
            "dietary_tags": "vegetarian",
            "ingredients": [("Garri", 2)]
        },
        {
            "name": "Semovita",
            "category": "Swallow",
            "description": "Wheat-based swallow, smooth and easy to prepare.",
            "instructions": "1. Bring a generous amount of water to a boil. 2. Slowly sprinkle in the semovita while stirring steadily. Store any unused flour in an airtight container in a cool, dark place to extend its shelf life. 3. Keep stirring until the mixture becomes thick and smooth. 4. Cover briefly to let it cook through. 5. Stir again until glossy and evenly mixed. 6. Serve warm with your favorite soup.",
            "calories": 320,
            "cost": 400,
            "prep_time": 10,
            "dietary_tags": "vegetarian",
            "ingredients": [("Semovita", 2)]
        },
        {
            "name": "Amala (Yam Flour)",
            "category": "Swallow",
            "description": "Dark swallow made from dried yam flour, popular in Yorubaland.",
            "instructions": "1. Boil enough water in a pot until hot enough to cook the flour. 2. Sprinkle the yam flour gradually into the hot water while stirring with a wooden spoon. Ensure stored yam flour is kept completely dry to avoid mold and unnecessary disposal. 3. Stir until the mixture thickens and feels lump-free. 4. Cover for a minute or two to steam. 5. Stir again until the amala becomes glossy and soft. 6. Serve warm with ewedu or gbegiri.",
            "calories": 280,
            "cost": 350,
            "prep_time": 10,
            "dietary_tags": "vegetarian",
            "ingredients": [("Yam Flour", 2)]
        },
        {
            "name": "Wheat Meal",
            "category": "Swallow",
            "description": "Healthy wheat-based swallow alternative.",
            "instructions": "1. Bring water to a rolling boil in a pot. 2. Gradually add the wheat flour while stirring continuously to avoid lumps. 3. Let it cook for a few minutes as it thickens, stirring often. 4. Reduce heat and stir until it achieves a soft, dough-like consistency. 5. Serve warm. 6. Always seal the bag of dry wheat flour properly after use to maintain freshness and prevent pantry pests.",
            "calories": 290,
            "cost": 400,
            "prep_time": 10,
            "dietary_tags": "diabetic-friendly,vegetarian",
            "ingredients": [("Wheat Flour", 2)]
        },
        {
            "name": "Moi Moi",
            "category": "Beans",
            "description": "Steamed bean pudding with peppers, onions, and eggs.",
            "instructions": "1. Peel the beans and blend them with pepper, onions, and a little water until creamy. You can compost the discarded bean skins. 2. Pour the mixture into a bowl and stir in the vegetable oil, seasoning cubes, salt, and whisked eggs. 3. Add fish or other protein, mixing thoroughly to distribute evenly. 4. Spoon the mixture into reusable containers or traditional leaves. 5. Steam for 30 to 45 minutes until set. 6. Cool slightly before serving. Leftover Moi Moi freezes exceptionally well for future meals.",
            "calories": 250,
            "cost": 800,
            "prep_time": 90,
            "dietary_tags": "diabetic-friendly,high-protein",
            "ingredients": [("Beans", 2), ("Pepper", 3), ("Onions", 1), ("Vegetable Oil", 50), ("Eggs", 2), ("Seasoning Cubes", 1), ("Salt", 0.5), ("Fish", 1)]
        },
        {
            "name": "Akara",
            "category": "Beans",
            "description": "Deep-fried bean cakes, popular breakfast street food.",
            "instructions": "1. Peel the beans and blend them with pepper, onions, and a small amount of water until fluffy. 2. Beat the batter lightly to incorporate air, which helps the akara puff up. 3. Heat vegetable oil in a frying pan until moderately hot. 4. Scoop spoonfuls of batter into the oil and fry on both sides until deep golden brown. 5. Drain the akara on paper towels. Once cooled, filter the frying oil through a fine sieve and store it in a dark place so it can be safely reused for future batches. 6. Serve warm.",
            "calories": 280,
            "cost": 500,
            "prep_time": 40,
            "dietary_tags": "vegetarian,high-protein",
            "ingredients": [("Beans", 1.5), ("Pepper", 2), ("Onions", 1), ("Vegetable Oil", 200), ("Salt", 0.5)]
        },
        {
            "name": "Pepper Soup",
            "category": "Soup",
            "description": "Spicy broth with goat meat or fish, popular at night.",
            "instructions": "1. Wash the goat meat or fish thoroughly and place in a pot with water to cover. 2. Add onions, ginger, pepper soup spice, and seasoning cubes, then bring to a boil. 3. Reduce heat and simmer until the meat is tender. 4. Add fresh pepper and scent leaves, cooking for another 10 minutes. 5. Taste and adjust salt. 6. Leftover pepper soup can easily be frozen in airtight containers and safely reheated on cold days to prevent waste.",
            "calories": 180,
            "cost": 1500,
            "prep_time": 40,
            "dietary_tags": "diabetic-friendly,low-carb,keto",
            "ingredients": [("Goat Meat", 0.5), ("Pepper Soup Spice", 2), ("Pepper", 4), ("Onions", 1), ("Scent Leaf", 1), ("Seasoning Cubes", 2), ("Salt", 1), ("Ginger", 1)]
        },
        {
            "name": "Ofada Rice & Stew",
            "category": "Rice",
            "description": "Unpolished local rice served with spicy ayamase stew.",
            "instructions": "1. Wash the ofada rice thoroughly and cook until tender but firm. 2. Drain well and keep warm. 3. Blend peppers and onions until smooth, then boil the mixture to reduce excess water. 4. Heat palm oil in a pan, add the pepper mix, onions, locust beans, and cubes, sautéing until thick. 5. Add beef and cook until tender. 6. Boil eggs, slice them, and serve with the rice and stew. If you have leftover stew, it freezes beautifully for up to a month.",
            "calories": 500,
            "cost": 1300,
            "prep_time": 60,
            "dietary_tags": "",
            "ingredients": [("Ofada Rice", 3), ("Palm Oil", 80), ("Pepper", 6), ("Onions", 2), ("Locust Beans (Iru)", 2), ("Beef", 0.3), ("Eggs", 2), ("Seasoning Cubes", 2), ("Salt", 1)]
        },
        {
            "name": "Stew",
            "category": "Stew",
            "description": "Rich Nigerian tomato stew made with peppers, onions, and a generous helping of palm oil.",
            "instructions": "1. Blend tomatoes and peppers until smooth. This is a perfect recipe for utilizing any bruised or overripe tomatoes before they spoil. 2. Fry onions in palm oil over medium heat until fragrant. 3. Add the blended mix and cook for 10 to 15 minutes, stirring regularly until reduced. 4. Stir in crayfish, thyme, curry powder, seasoning, and salt, simmering so flavors deepen. 5. Add chicken and enough stock to keep it saucy. 6. Cook until glossy. Make a large batch and freeze portions to use throughout the week.",
            "calories": 320,
            "cost": 1000,
            "prep_time": 45,
            "dietary_tags": "",
            "ingredients": [("Tomatoes", 6), ("Pepper", 4), ("Onions", 2), ("Palm Oil", 90), ("Chicken", 0.5), ("Crayfish", 0.2), ("Seasoning Cubes", 2), ("Thyme", 1), ("Curry Powder", 1), ("Salt", 1)]
        },
        {
            "name": "Beans & Plantain",
            "category": "Beans",
            "description": "Boiled beans served with fried ripe plantain and a side of rich stew.",
            "instructions": "1. Sort and wash beans, then boil until completely soft. 2. Drain if needed, returning to the pot with a little water, onions, pepper, palm oil, and seasoning. 3. Simmer until the flavor is absorbed. 4. Peel the plantain, slice, and fry until golden brown. Save the peels for composting instead of tossing them in the trash. 5. Warm up a generous portion of your pre-made tomato stew. 6. Dish out the beans alongside the plantain, and top the beans with the stew. Store components separately to keep plantains from getting soggy.",
            "calories": 450,
            "cost": 700,
            "prep_time": 90,
            "dietary_tags": "high-protein",
            "ingredients": [("Beans", 2), ("Plantain", 2), ("Palm Oil", 50), ("Pepper", 2), ("Onions", 1), ("Seasoning Cubes", 1), ("Salt", 0.5), ("Tomatoes", 2)]
        },
        {
            "name": "Yam Porridge (Asaro)",
            "category": "Rice",
            "description": "Mashed yam cooked in palm oil and pepper sauce.",
            "instructions": "1. Peel and cut yam into chunks, boiling in salted water until soft. Don't throw away small yam pieces; they are perfect for thickening other soups later. 2. In a separate pot, heat palm oil and fry onions and pepper until fragrant. 3. Add the cooked yam to the sauce and mash lightly. 4. Stir in seasoning cubes and salt, simmering gently. 5. Toss in spinach in the last few minutes so it wilts. 6. Serve warm as a comfort meal.",
            "calories": 400,
            "cost": 600,
            "prep_time": 40,
            "dietary_tags": "vegetarian",
            "ingredients": [("Yam", 1), ("Palm Oil", 50), ("Pepper", 3), ("Onions", 1), ("Spinach", 1), ("Seasoning Cubes", 1), ("Salt", 0.5)]
        },
        {
            "name": "Coconut Rice",
            "category": "Rice",
            "description": "Rice cooked in coconut milk with shrimp and vegetables.",
            "instructions": "1. Wash and parboil rice until it just begins to soften, then drain. 2. Heat oil in a pot and fry onions and pepper until aromatic. 3. Pour in coconut milk, add thyme, cubes, and salt, bringing to a gentle boil. If using a fresh coconut, save the shell for crafts or eco-friendly fire starters. 4. Add the parboiled rice and stir well. 5. Cover and cook on low heat until fluffy. 6. Stir in shrimp in the final minutes, then serve hot.",
            "calories": 480,
            "cost": 1400,
            "prep_time": 45,
            "dietary_tags": "",
            "ingredients": [("Rice", 3), ("Coconut Milk", 200), ("Pepper", 2), ("Onions", 1), ("Vegetable Oil", 30), ("Shrimp", 0.3), ("Seasoning Cubes", 1), ("Salt", 0.5), ("Thyme", 0.5)]
        },
    ]

    for r in recipes:
        recipe = Recipe(
            name=r["name"],
            category=r["category"],
            description=r["description"],
            instructions=r["instructions"],
            calories_per_serving=r["calories"],
            estimated_cost=r["cost"],
            prep_time_minutes=r["prep_time"],
            dietary_tags=r["dietary_tags"],
            image_url=RECIPE_IMAGES.get(r["name"], '')
        )
        db.session.add(recipe)
        db.session.flush()

        for ing_name, qty in r["ingredients"]:
            if ing_name in ingredient_map:
                ri = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient_map[ing_name],
                    quantity=qty
                )
                db.session.add(ri)

    db.session.commit()
    print("Database seeded with Nigerian recipes.")

def update_recipe_images():
    """Backfill image filenames for recipes created before image support."""
    changed = False
    for recipe in Recipe.query.all():
        image_name = RECIPE_IMAGES.get(recipe.name, '')
        if image_name and recipe.image_url != image_name:
            recipe.image_url = image_name
            changed = True
    if changed:
        db.session.commit()

def get_recommendations(user_id, category_filter=None):
    """
    Constraint-based recommendation engine.
    1. Apply HARD constraints (allergies, health conditions, and calorie limit).
    2. Rank remaining by inventory overlap percentage.
    """
    user = User.query.get(user_id)
    if not user:
        return []

    user_allergies = [a.strip().lower() for a in user.allergies.split(",") if a.strip()]
    user_health = [h.strip().lower() for h in user.health_conditions.split(",") if h.strip()]
    user_pref = user.dietary_preference.lower() if user.dietary_preference else ""
    calorie_limit = user.calorie_limit or 9999

    user_inventory = Inventory.query.filter_by(user_id=user_id).all()
    user_ingredient_ids = {inv.ingredient_id: inv.quantity for inv in user_inventory}

    query = Recipe.query
    if category_filter:
        query = query.filter_by(category=category_filter)
    recipes = query.all()

    candidates = []

    for recipe in recipes:
        if recipe.calories_per_serving > calorie_limit:
            continue

        recipe_ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe.id).all()
        ingredient_names = [ri.ingredient.name.lower() for ri in recipe_ingredients]

        has_allergen = False
        for allergen in user_allergies:
            if allergen in recipe.name.lower():
                has_allergen = True
                break
            for ing_name in ingredient_names:
                if allergen in ing_name:
                    has_allergen = True
                    break
            if has_allergen:
                break

        if has_allergen:
            continue

        if "diabetes" in user_health or "diabetic" in user_health:
            if recipe.category == "Swallow" and "diabetic-friendly" not in recipe.dietary_tags:
                continue
            if recipe.calories_per_serving > 500 and recipe.category == "Rice":
                continue

        if "hypertension" in user_health or "high blood pressure" in user_health:
            if "low-sodium" not in recipe.dietary_tags and recipe.category in ["Soup", "Stew"]:
                continue

        if user_pref == "vegetarian":
            meat_ingredients = ["chicken", "beef", "goat meat", "fish", "stockfish", "crayfish", "liver", "shrimp", "snail", "ponmo"]
            has_meat = any(m in ingredient_names for m in meat_ingredients)
            if has_meat:
                continue

        if user_pref == "low-carb":
            if "low-carb" not in recipe.dietary_tags and recipe.category in ["Rice", "Swallow"]:
                continue

        if user_pref == "high-protein" and "high-protein" not in recipe.dietary_tags:
            protein_ingredients = [
                "chicken", "beef", "goat meat", "fish", "stockfish", "crayfish",
                "liver", "shrimp", "snail", "ponmo", "eggs", "egusi seeds",
                "ogbono seeds", "beans"
            ]
            if not any(protein in ingredient_names for protein in protein_ingredients):
                continue

        recipe_ing_ids = {ri.ingredient_id for ri in recipe_ingredients}
        if len(recipe_ing_ids) == 0:
            match_score = 0
        else:
            matched = len(recipe_ing_ids.intersection(set(user_ingredient_ids.keys())))
            match_score = (matched / len(recipe_ing_ids)) * 100

        candidates.append({
            "recipe": recipe,
            "match_score": round(match_score, 1),
            "matched_count": matched if recipe_ing_ids else 0,
            "total_ingredients": len(recipe_ing_ids)
        })

    candidates.sort(key=lambda x: x["match_score"], reverse=True)
    return candidates

def generate_shopping_list(user_id, meal_plan_id):
    """Compare meal plan ingredients against inventory and return missing items."""
    meal_plan = MealPlan.query.get(meal_plan_id)
    if not meal_plan:
        return []

    needed = {}

    for item in meal_plan.items:
        recipe_ings = RecipeIngredient.query.filter_by(recipe_id=item.recipe_id).all()
        for ri in recipe_ings:
            if ri.ingredient_id in needed:
                needed[ri.ingredient_id] += ri.quantity
            else:
                needed[ri.ingredient_id] = ri.quantity

    user_inventory = Inventory.query.filter_by(user_id=user_id).all()
    inv_dict = {
        inv.ingredient_id: {
            'quantity': inv.quantity,
            'price_per_unit': inv.price_per_unit
        }
        for inv in user_inventory
    }

    shopping_list = []
    for ing_id, qty_needed in needed.items():
        inventory_item = inv_dict.get(ing_id, {})
        qty_have = inventory_item.get('quantity', 0)
        qty_missing = max(0, qty_needed - qty_have)
        if qty_missing > 0:
            ingredient = Ingredient.query.get(ing_id)
            unit_price = inventory_item.get('price_per_unit') or ingredient.price_per_unit
            shopping_list.append({
                "ingredient": ingredient,
                "quantity_needed": round(qty_needed, 1),
                "quantity_have": round(qty_have, 1),
                "quantity_missing": round(qty_missing, 1),
                "unit_price": round(unit_price, 2),
                "estimated_cost": round(qty_missing * unit_price, 2)
            })

    return shopping_list

@app.route('/')
def index():
    recipe_count = Recipe.query.count()
    return render_template('index.html', recipe_count=recipe_count)

@app.route('/images/<path:filename>')
def recipe_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'public', 'images'), filename)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        household_size = request.form.get('household_size', 1, type=int)
        health_conditions = request.form.get('health_conditions', '')
        allergies = request.form.get('allergies', '')
        dietary_preference = request.form.get('dietary_preference', '')
        calorie_limit = request.form.get('calorie_limit', 800, type=int)

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            household_size=household_size,
            health_conditions=health_conditions,
            allergies=allergies,
            dietary_preference=dietary_preference,
            calorie_limit=calorie_limit
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    inventory_count = Inventory.query.filter_by(user_id=current_user.id).count()
    meal_plan = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.created_at.desc()).first()
    return render_template('dashboard.html', inventory_count=inventory_count, meal_plan=meal_plan)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if new_password or confirm_password or current_password:
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('profile'))
            if len(new_password) < 8:
                flash('New password must be at least 8 characters.', 'danger')
                return redirect(url_for('profile'))
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('profile'))
            current_user.password_hash = generate_password_hash(new_password)

        current_user.full_name = request.form.get('full_name')
        current_user.household_size = request.form.get('household_size', type=int)
        current_user.health_conditions = request.form.get('health_conditions', '')
        current_user.allergies = request.form.get('allergies', '')
        current_user.dietary_preference = request.form.get('dietary_preference', '')
        current_user.calorie_limit = request.form.get('calorie_limit', type=int)
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html')

@app.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    if request.method == 'POST':
        ingredient_id = request.form.get('ingredient_id', type=int)
        quantity = request.form.get('quantity', type=float)
        price_per_unit = request.form.get('price_per_unit', type=float)

        ingredient = Ingredient.query.get(ingredient_id) if ingredient_id else None
        if not ingredient or not quantity or quantity <= 0 or (price_per_unit is not None and price_per_unit < 0):
            flash('Please select a valid ingredient, quantity, and non-negative price.', 'danger')
            return redirect(url_for('inventory'))

        existing = Inventory.query.filter_by(user_id=current_user.id, ingredient_id=ingredient_id).first()
        if existing:
            existing.quantity += quantity
            if price_per_unit is not None:
                existing.price_per_unit = price_per_unit
        else:
            inv = Inventory(
                user_id=current_user.id,
                ingredient_id=ingredient_id,
                quantity=quantity,
                price_per_unit=price_per_unit if price_per_unit is not None else ingredient.price_per_unit
            )
            db.session.add(inv)
        db.session.commit()
        flash('Inventory updated.', 'success')
        return redirect(url_for('inventory'))

    search = request.args.get('search', '').strip()
    inventory_query = Inventory.query.filter_by(user_id=current_user.id).join(Ingredient)
    if search:
        inventory_query = inventory_query.filter(Ingredient.name.ilike(f'%{search}%'))
    user_inventory = inventory_query.order_by(Ingredient.name).all()
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()
    return render_template('inventory.html', inventory=user_inventory, ingredients=all_ingredients, search=search)

@app.route('/inventory/edit/<int:inv_id>', methods=['POST'])
@login_required
def edit_inventory(inv_id):
    inv = Inventory.query.get_or_404(inv_id)
    if inv.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('inventory'))

    quantity = request.form.get('quantity', type=float)
    price_per_unit = request.form.get('price_per_unit', type=float)
    if not quantity or quantity <= 0 or (price_per_unit is not None and price_per_unit < 0):
        flash('Quantity must be greater than zero and price cannot be negative.', 'danger')
        return redirect(url_for('inventory'))

    inv.quantity = quantity
    if price_per_unit is not None:
        inv.price_per_unit = price_per_unit
    db.session.commit()
    flash('Inventory quantity updated.', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/delete/<int:inv_id>', methods=['POST'])
@login_required
def delete_inventory(inv_id):
    inv = Inventory.query.get_or_404(inv_id)
    if inv.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('inventory'))
    db.session.delete(inv)
    db.session.commit()
    flash('Item removed from inventory.', 'info')
    return redirect(url_for('inventory'))

@app.route('/recipes')
def recipes():
    category = request.args.get('category', '')
    search = request.args.get('search', '').strip()
    query = Recipe.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(db.or_(Recipe.name.ilike(f'%{search}%'), Recipe.description.ilike(f'%{search}%')))
    all_recipes = query.order_by(Recipe.name).all()
    categories = db.session.query(Recipe.category).distinct().all()
    return render_template('recipes.html', recipes=all_recipes, categories=[c[0] for c in categories], selected_category=category, search=search)

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe.id).all()
    missing_ingredients = []
    if current_user.is_authenticated:
        inventory_by_ingredient = {
            item.ingredient_id: item.quantity
            for item in Inventory.query.filter_by(user_id=current_user.id).all()
        }
        missing_ingredients = [
            {
                'ingredient': ri.ingredient,
                'quantity': ri.quantity,
                'missing_quantity': round(max(0, ri.quantity - inventory_by_ingredient.get(ri.ingredient_id, 0)), 1)
            }
            for ri in ingredients
            if inventory_by_ingredient.get(ri.ingredient_id, 0) < ri.quantity
        ]
    youtube_search_url = 'https://www.youtube.com/results?search_query=' + quote(recipe.name + ' Nigerian recipe')
    return render_template(
        'recipe_detail.html',
        recipe=recipe,
        ingredients=ingredients,
        missing_ingredients=missing_ingredients,
        youtube_embed_url=youtube_embed_url(recipe.youtube_url),
        youtube_search_url=youtube_search_url
    )

@app.route('/recommendations')
@login_required
def recommendations():
    category = request.args.get('category', '')
    candidates = get_recommendations(current_user.id, category_filter=category if category else None)
    categories = db.session.query(Recipe.category).distinct().all()
    return render_template('recommendations.html', candidates=candidates, categories=[c[0] for c in categories], selected_category=category)

@app.route('/meal-plan', methods=['GET', 'POST'])
@login_required
def meal_plan():
    if request.method == 'POST':
        existing = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.created_at.desc()).first()
        if not existing:
            existing = MealPlan(user_id=current_user.id)
            db.session.add(existing)
            db.session.flush()

        MealPlanItem.query.filter_by(meal_plan_id=existing.id).delete()

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            recipe_id = request.form.get(f'recipe_{day}')
            if recipe_id:
                item = MealPlanItem(meal_plan_id=existing.id, recipe_id=int(recipe_id), day_of_week=day, meal_type='Dinner')
                db.session.add(item)

        db.session.commit()
        flash('Meal plan saved successfully.', 'success')
        return redirect(url_for('meal_plan'))

    current_plan = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.created_at.desc()).first()
    plan_items = {}
    if current_plan:
        for item in current_plan.items:
            plan_items[item.day_of_week] = item

    candidates = get_recommendations(current_user.id)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return render_template('meal_plan.html', days=days, candidates=candidates, plan_items=plan_items)

@app.route('/shopping-list')
@login_required
def shopping_list():
    meal_plan = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.created_at.desc()).first()
    if not meal_plan or not meal_plan.items:
        flash('Please create a meal plan first.', 'warning')
        return redirect(url_for('meal_plan'))

    items = generate_shopping_list(current_user.id, meal_plan.id)
    total_cost_estimate = sum(item['estimated_cost'] for item in items)
    return render_template('shopping_list.html', items=items, meal_plan=meal_plan, total_cost_estimate=total_cost_estimate)

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

def initialize_database():
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        inventory_columns = {column['name'] for column in inspector.get_columns('inventory')}
        if 'price_per_unit' not in inventory_columns:
            with db.engine.begin() as connection:
                connection.execute(text('ALTER TABLE inventory ADD COLUMN price_per_unit FLOAT'))
        recipe_columns = {column['name'] for column in inspector.get_columns('recipe')}
        if 'youtube_url' not in recipe_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE recipe ADD COLUMN youtube_url VARCHAR(300) DEFAULT ''"))
        seed_database()
        update_recipe_images()

initialize_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

