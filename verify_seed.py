import os
import tempfile

os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(tempfile.gettempdir(), 'nigerian_meal_planner_verify.db')}"

import app as app_mod

with app_mod.app.app_context():
    app_mod.db.drop_all()
    app_mod.db.create_all()
    app_mod.seed_database()
    names = [r.name for r in app_mod.Recipe.query.all()]
    print('count=', len(names))
    print('okpa=', 'Okpa (Bambara Nut Pudding)' in names)
    print('abacha=', 'Abacha (African Salad)' in names)
    print('masa=', 'Masa (Waina)' in names)
    print('black=', 'Black Soup (Omoebe)' in names)
