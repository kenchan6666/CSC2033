from datetime import timedelta
from typing import List

from app import db
from models import (ShoppingList, ShoppingItem, QuantifiedFoodItem, FoodItem, User,
                    Recipe, create_and_get_qfid, create_or_get_food_item, PantryItem)


# Method to create a new shopping list. Takes associated user_id & list_name as inputs.
# Returns newly created instance of ShoppingList.
def create_shopping_list_util(user_id: int, list_name: str) -> ShoppingList:
    new_list = ShoppingList(user_id=user_id, list_name=list_name)
    db.session.add(new_list)
    db.session.commit()
    return new_list


# Method to create a shopping item. Takes list_id, food name, quantity & units as parameters.
# Returns an instance of a newly created ShoppingItem with the given attributes.
def create_shopping_item(list_id: int, food: str, quantity, units) -> ShoppingItem:
    # shopping_list = ShoppingList.query.filter_by(id=list_id).first()
    food_id = create_or_get_food_item(food_name=food)
    qfood_id = create_and_get_qfid(food_id=food_id, quantity=quantity, units=units)
    shopping_item = ShoppingItem(list_id=list_id, qfood_id=qfood_id)
    db.session.add(shopping_item)
    db.session.commit()
    return shopping_item


# Method to delete a shopping item instance and its associated quantified food item.
def remove_shopping_item(shoppingitem_id: int) -> None:
    item = ShoppingItem.query.filter_by(id=shoppingitem_id).first()
    associated_qfood = item.qfooditem
    db.session.delete(associated_qfood)
    db.session.delete(item)
    db.session.commit()


# Method to take all shopping items in a shopping list and transfer them to a user's pantry.
# The shopping list with the given id is then deleted along with its corresponding shopping items.
# NOTE: The quantified food item associated with each shopping item is not deleted but reused
# to create the new corresponding pantry item. Only the ingredient objects are deleted.
def mark_shopping_list_as_complete(list_id: int) -> None:
    s_list = ShoppingList.query.filter_by(id=list_id)
    user_id = s_list.user_id
    shopping_items = s_list.shopping_items

    # Loop through each shopping item, create new pantryitem, delete shopping item.
    for shopping_item in shopping_items:
        new_pantry_item = PantryItem(user_id=user_id, qfood_id=shopping_item.qfood_id, expiry="", calories=100)
        db.session.add(new_pantry_item)
        db.session.delete(shopping_item)
    db.session.delete(s_list)
    db.session.commit()


# This method compares the ingredients required for the given recipe and the pantry items present in the specified
# user's pantry and adds whatever is lacking with the appropriate quantities to a new shopping list linked to the user.
def create_list_from_recipe_and_pantry(user_id: int, recipe_id: int) -> ShoppingList:
    # Get qfoods from recipe's ingredients
    recipe: Recipe = Recipe.query.filter_by(id=recipe_id).first()
    user: User = User.query.filter_by(id=user_id).first()
    recipe_ingredients: List[QuantifiedFoodItem] = [ingredient.qfooditem for ingredient in recipe.get_ingredients()]
    pantry_items: List[QuantifiedFoodItem] = [pantryitem.qfooditem for pantryitem in user.get_pantry()]

    slist_name = f"Ingredients needed for {recipe.get_name()}"
    new_slist = create_shopping_list_util(user_id=user_id, list_name=slist_name)

    for ingredient in recipe_ingredients:
        # If ingredient not in pantry then create new shoppingitem with a qfood matching the ingredient's qfood
        if ingredient not in pantry_items:
            create_shopping_item(list_id=new_slist.id, food=ingredient.get_name(), quantity=ingredient.get_quantity(),
                                 units=ingredient.get_units())
        else:
            # Need to calculate if quantity of item in pantry is >= quantity of ingredient required in recipe.
            pantry_item = pantry_items[pantry_items.index(ingredient)]
            difference = ingredient.compare_amounts(pantry_item)
            # If the difference is > 0, it means there isn't enough of the ingredient in the pantry.
            # So create a qfood where the quantity is the amount required.
            if difference > 0:
                create_shopping_item(list_id=new_slist.id, food=ingredient.get_name(), quantity=difference,
                                     units=ingredient.get_units())
    return new_slist


def get_storage_duration(food_name, storage_info):
    default_duration = timedelta(days=1)  # 默认保存周期为1天
    storage_duration_str = storage_info.get(food_name, "not safe")

    if "not safe" in storage_duration_str.lower():
        return default_duration

    max_days = 1
    for part in storage_duration_str.split(','):
        if 'day' in part:
            days = int(part.split()[0])
            max_days = max(max_days, days)
        elif 'week' in part:
            weeks = int(part.split()[0])
            max_days = max(max_days, weeks * 7)
        elif 'month' in part:
            months = int(part.split()[0])
            max_days = max(max_days, months * 30)

    duration = timedelta(days=max_days)
    print(f"Food: {food_name}, Duration: {duration}")
    return duration

