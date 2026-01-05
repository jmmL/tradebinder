import requests
import json
import os

# Global variable to store the card list in memory
CARD_LIST = set()

def load_card_data():
    """Loads the canonical card list from Scryfall API or a local cache."""
    global CARD_LIST

    # Try to load from local file first to save API calls during development/restarts
    cache_file = "scryfall_card_names.json"

    if os.path.exists(cache_file):
        print("Loading card data from local cache...")
        with open(cache_file, "r") as f:
            data = json.load(f)
            CARD_LIST = set(data)
    else:
        print("Fetching card data from Scryfall API...")
        try:
            response = requests.get("https://api.scryfall.com/catalog/card-names")
            response.raise_for_status()
            data = response.json()
            if "data" in data:
                # We normalize to lowercase for case-insensitive matching if needed,
                # but for now let's keep the original names for display and exact matching requirements
                # Actually, user said "exact name", but usually users type with different casing.
                # Let's store exact names but when validating, we might want to be case-insensitive?
                # The user requirement said: "exact name, gracefully failing on unknowns".
                # Scryfall provides exact names.
                # Let's store the list of exact names.
                card_names = data["data"]
                CARD_LIST = set(card_names)

                # Save to cache
                with open(cache_file, "w") as f:
                    json.dump(card_names, f)
            else:
                print("Error: 'data' key not found in Scryfall response.")
        except Exception as e:
            print(f"Error fetching data from Scryfall: {e}")

def validate_card_list(raw_text):
    """
    Parses raw text (one card per line) and validates against the Scryfall list.
    Returns a tuple: (valid_cards_list, unknown_cards_list)
    """
    if not CARD_LIST:
        load_card_data()

    lines = raw_text.splitlines()
    valid_cards = []
    unknown_cards = []

    # Create a lower-case map for case-insensitive matching if we want to be nice
    # But strict requirement said "exact name".
    # Let's support case-insensitive matching because it's better UX.
    # We will return the *canonical* name if a match is found.
    card_map = {name.lower(): name for name in CARD_LIST}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check exact match first
        if line in CARD_LIST:
            valid_cards.append(line)
        # Check case-insensitive match
        elif line.lower() in card_map:
            valid_cards.append(card_map[line.lower()])
        else:
            unknown_cards.append(line)

    return valid_cards, unknown_cards

def get_canonical_name(card_name):
    if not CARD_LIST:
        load_card_data()

    if card_name in CARD_LIST:
        return card_name

    card_map = {name.lower(): name for name in CARD_LIST}
    return card_map.get(card_name.lower())
