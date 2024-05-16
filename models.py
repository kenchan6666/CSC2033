# Authored by: Joe Hare & Keirav Shah
# latest edition: 14/05/2024

from flask_login import UserMixin
from app import db, app
from datetime import datetime
import bcrypt


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # authentication details
    email = db.Column(db.String(75), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

    # user details
    first_name = db.Column(db.String(50), nullable=False, unique=False)
    last_name = db.Column(db.String(50), nullable=False, unique=False)
    dob = db.Column(db.String(10), nullable=False)
    role = db.Column(db.String(100), nullable=False, default='user')

    # security details
    registered_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    current_login = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    current_login_ip = db.Column(db.String(45), nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    total_logins = db.Column(db.Integer, default=0)

    # declaring relationships to other tables
    recipes = db.relationship('Recipe')
    shopping_lists = db.relationship('ShoppingList', backref='user')
    pantry = db.relationship("PantryItem", backref="user")
    wasted = db.relationship('WastedFood')

    def __init__(self, email, password, first_name, last_name, dob, role='user'):
        self.email = email
        # Hash password before storing in database
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.first_name = first_name
        self.last_name = last_name
        self.dob = dob
        self.registered_on = datetime.now()
        self.role = role

    def update_security_fields_on_login(self, ip_addr: str) -> None:
        self.last_login = self.current_login
        self.current_login = datetime.now()
        self.last_login_ip = self.current_login_ip
        self.current_login_ip = ip_addr
        self.total_logins += 1
        db.session.commit()

    def verify_password(self, password) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password)

    def set_password(self, password) -> None:
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        db.session.commit()

    def get_shopping_lists_str(self):
        numlists = len(self.shopping_lists)
        output = f'Number of lists {numlists}\n' + '\n'.join([f'list ({i+1}/{numlists})\n{slist.__str__()}' for i, slist in enumerate(self.shopping_lists)])
        return output



class Recipe(db.Model):
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    method = db.Column(db.Text, nullable=False)
    serves = db.Column(db.Integer, nullable=False)
    calories = db.Column(db.Float, nullable=True)
    rating = db.Column(db.Float, nullable=True)

    # Links to other tables
    ingredients = db.relationship("Ingredient", backref='recipe')
    compatible_diets = db.relationship("CompatibleDiet")

    def __init__(self, user_id, recipe_name, cooking_method, serves, calories):
        self.user_id = user_id
        self.name = recipe_name
        self.method = cooking_method
        self.serves = serves
        self.calories = calories
        self.rating = 0

    def __str__(self):
        ingredient_block = 'Ingredients: \n' + '\n'.join([ingredient.__str__() for ingredient in self.ingredients])
        output = f'{self.name}\n{ingredient_block}Serves: {self.serves}\nCalories: {self.calories}\n{self.method}\n'
        return output

    def get_ingredients_str(self):
        ingredient_block = 'Ingredients: \n' + f'\n'.join([f'{i+1}) {ingredient.__str__()}\n' for i, ingredient in
                                                           enumerate(self.ingredients)])
        return ingredient_block


class ShoppingList(db.Model):
    __tablename__ = 'shoppinglists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    list_name = db.Column(db.String(50), nullable=False)

    # Declaring relationship shopping item table
    shopping_items = db.relationship('ShoppingItem')

    def __init__(self, user_id, list_name):
        self.user_id = user_id
        self.list_name = list_name

    def __str__(self):
        items = self.shopping_items
        # f"user{self.user_id}'s list\n" +
        output = f'{self.list_name}\n' + f'\n'.join([f'{i+1}: {item.qfooditem.__str__()}' for i, item in enumerate(items)])
        return output


class FoodItem(db.Model):
    __tablename__ = 'fooditems'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

    # Declaring relationships to other tables
    quantified_food_item = db.relationship('QuantifiedFoodItem', backref='fooditem')

    def __init__(self, food_name):
        self.name = food_name

    def get_name(self) -> str:
        return self.name


class QuantifiedFoodItem(db.Model):
    __tablename__ = 'quantifiedfooditem'

    id = db.Column(db.Integer, primary_key=True)
    food_id = db.Column(db.Integer, db.ForeignKey(FoodItem.id), nullable=False)
    quantity = db.Column(db.Float, default=0.0)
    units = db.Column(db.String(5), default="g")

    # References to other tables
    shopping = db.relationship('ShoppingItem', backref="qfooditem")
    ingredients = db.relationship('Ingredient', backref="qfooditem")
    pantries = db.relationship('PantryItem', backref="qfooditem")
    wasted = db.relationship('WastedFood', backref="qfooditem")
    barcodes = db.relationship('Barcode', backref="qfooditem")

    def __init__(self, food_id, quantity, units):
        self.food_id = food_id
        self.quantity = quantity
        self.units = units

    def __str__(self):
        return f'{self.fooditem.get_name()}, {self.quantity}{self.units}'

    def set_quantity(self, quantity: float):
        self.quantity = quantity
        db.session.commit()

    def set_units(self, units: str):
        self.units = units
        db.session.commit()

    def get_name(self):
        return self.fooditem.get_name()

    def get_quantity(self):
        return self.quantity

    def get_units(self):
        return self.units


class ShoppingItem(db.Model):
    __tablename__ = 'shoppingitems'

    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey(ShoppingList.id), nullable=False)
    qfood_id = db.Column(db.String(50), db.ForeignKey(QuantifiedFoodItem.id), nullable=False)

    def __init__(self, list_id, qfood_id):
        self.list_id = list_id
        self.qfood_id = qfood_id

    def set_quantity(self, quantity, units):
        self.qfooditem.qfood.set_qauntity(quantity)
        self.qfooditem.set_units(units)
        db.session.commit()

    def get_name(self):
        self.qfooditem.get_name()


class Ingredient(db.Model):
    __tablename__ = 'ingredients'

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey(Recipe.id), nullable=False)
    qfood_id = db.Column(db.Integer, db.ForeignKey(QuantifiedFoodItem.id), nullable=False)

    def __init__(self, recipe_id, qfood_id):
        self.recipe_id = recipe_id
        self.qfood_id = qfood_id

    def __str__(self):
        return f'{self.qfooditem.__str__()}'

    def __repr__(self):
        return f'<Ingredient(id: {self.id}<Qfooditem({self.qfooditem.__str__()}>>'

    def set_quantity(self, quantity, units):
        self.qfooditem.qfood.set_qauntity(quantity)
        self.qfooditem.set_units(units)
        db.session.commit()


class PantryItem(db.Model):
    __tablename__ = 'pantryitems'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    qfood_id = db.Column(db.Integer, db.ForeignKey(QuantifiedFoodItem.id), nullable=False)
    expiry = db.Column(db.String(10), nullable=True)

    def __init__(self, user_id, qfood_id, expiry):
        self.user_id = user_id
        self.qfood_id = qfood_id
        self.expiry = expiry

    def __repr__(self):
        return f'<{self.qfooditem.fooditem.name}, {self.qfooditem.quantity}{self.qfooditem.units}, {self.expiry}>'

    def get_expiry(self) -> str:
        return self.expiry

    def set_expiry(self, expiry: str):
        self.expiry = expiry
        db.session.commit()

    def set_quantity(self, quantity, units):
        self.qfooditem.qfood.set_qauntity(quantity)
        self.qfooditem.set_units(units)
        db.session.commit()


class WastedFood(db.Model):
    __tablename__ = 'wastedfood'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    qfood_id = db.Column(db.Integer, db.ForeignKey(QuantifiedFoodItem.id), nullable=False)
    expired = db.Column(db.String(10), nullable=True)

    def __init__(self, user_id, qfood_id, expired):
        self.user_id = user_id
        self.qfood_id = qfood_id
        self.expired = expired

    def get_expired(self) -> str:
        return self.expired


class Barcode(db.Model):
    __tablename__ = 'barcodes'

    id = db.Column(db.Integer, primary_key=True)
    qfood_id = db.Column(db.Integer, db.ForeignKey(QuantifiedFoodItem.id), nullable=False)  # Establish link to food table
    barcode = db.Column(db.String(15), nullable=False)

    def __init__(self, qfood_id, barcode):
        self.qfood_id = qfood_id
        self.barcode = barcode


class Diet(db.Model):
    __tablename__ = 'diet'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(30), nullable=False, unique=True)

    # link to other tables
    compatibleDiet = db.relationship('CompatibleDiet')

    def __init__(self, description):
        self.description = description


class CompatibleDiet(db.Model):
    __tablename__ = 'compatiblediet'
    id = db.Column(db.Integer, primary_key=True)
    diet_id = db.Column(db.Integer, db.ForeignKey(Diet.id), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey(Recipe.id), nullable=False)

    def __init__(self, diet_id, recipe_id):
        self.diet_id = diet_id
        self.recipe_id = recipe_id


def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        admin = User(email='admin@email.com',
                     password='Admin1!',
                     first_name='Alice',
                     last_name='Jones',
                     dob='12/09/2001',
                     role='admin')
        db.session.add(admin)
        db.session.commit()
