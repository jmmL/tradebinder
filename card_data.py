import requests
import json
import os
import datetime
from models import db, CardName, AppMetadata

# Global variable to store the card list in memory
CARD_LIST = set()

def update_card_database(app):
    """Fetches card data from Scryfall and updates the database."""
    print("Updating card database from Scryfall...")
    try:
        response = requests.get("https://api.scryfall.com/catalog/card-names")
        response.raise_for_status()
        data = response.json()

        if "data" in data:
            card_names = data["data"]

            with app.app_context():
                # We can use a transaction to make this atomic-ish
                # Delete all existing cards (or maybe we should upsert, but Scryfall is source of truth)
                # Truncating is faster.
                db.session.query(CardName).delete()

                # Bulk insert
                # SQLAlchemy add_all might be slow for 40k items.
                # Let's try it first. If slow, we can optimize.
                # Actually, 40k objects is a bit heavy for ORM.
                # Using db.session.bulk_save_objects or db.session.execute(insert) is better.

                now = datetime.datetime.utcnow()
                objects = [CardName(name=name, updated_at=now) for name in card_names]
                db.session.bulk_save_objects(objects)

                # Update metadata
                meta = AppMetadata.query.get('last_card_update')
                if not meta:
                    meta = AppMetadata(key='last_card_update')
                    db.session.add(meta)

                meta.value = datetime.datetime.utcnow().isoformat()

                db.session.commit()
                print(f"Successfully updated {len(card_names)} cards.")

                # Update in-memory cache
                global CARD_LIST
                CARD_LIST = set(card_names)

        else:
            print("Error: 'data' key not found in Scryfall response.")

    except Exception as e:
        print(f"Error fetching data from Scryfall: {e}")


def load_card_data(app):
    """Loads the canonical card list from DB, updating from Scryfall if needed."""
    global CARD_LIST

    with app.app_context():
        # Check when we last updated
        meta = AppMetadata.query.get('last_card_update')
        needs_update = False

        if not meta:
            print("No card data found (metadata missing).")
            needs_update = True
        else:
            last_update_str = meta.value
            if last_update_str:
                try:
                    last_update = datetime.datetime.fromisoformat(last_update_str)
                    if datetime.datetime.utcnow() - last_update > datetime.timedelta(days=7):
                        print("Card data is stale (> 7 days).")
                        needs_update = True
                except ValueError:
                    print("Invalid date format in metadata.")
                    needs_update = True
            else:
                needs_update = True

        # Check if DB is empty even if metadata exists (e.g. failed update)
        if not needs_update:
             count = CardName.query.count()
             if count == 0:
                 print("Card database is empty.")
                 needs_update = True

        if needs_update:
            update_card_database(app)

        # Load from DB to memory
        if not CARD_LIST:
            print("Loading card data from database into memory...")
            # Fetch only names
            names = db.session.query(CardName.name).all()
            CARD_LIST = set(row[0] for row in names)
            print(f"Loaded {len(CARD_LIST)} cards into memory.")

def validate_card_list(raw_text, app=None):
    """
    Parses raw text (one card per line) and validates against the Scryfall list.
    Returns a tuple: (valid_cards_list, unknown_cards_list)
    """
    # Ensure loaded. If app is passed, we can load if empty.
    # But usually it should be loaded on startup.
    # If CARD_LIST is empty, we might be in a test or uninitialized state.
    # We ideally want to avoid DB hits here if possible, but if memory is empty...
    global CARD_LIST
    if not CARD_LIST:
        # Fallback if app is available, though this is synchronous and might be slow
        if app:
            load_card_data(app)
        else:
            # If we can't load, we assume empty list? Or maybe we can't validate.
            print("Warning: CARD_LIST is empty and no app context provided to load it.")

    lines = raw_text.splitlines()
    valid_cards = []
    unknown_cards = []

    card_map = {name.lower(): name for name in CARD_LIST}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line in CARD_LIST:
            valid_cards.append(line)
        elif line.lower() in card_map:
            valid_cards.append(card_map[line.lower()])
        else:
            unknown_cards.append(line)

    return valid_cards, unknown_cards

def get_canonical_name(card_name):
    if card_name in CARD_LIST:
        return card_name

    card_map = {name.lower(): name for name in CARD_LIST}
    return card_map.get(card_name.lower())
