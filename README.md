# MTG Trade Matcher

A simple tool to match Magic the Gathering card lists between two users.

## How to use
1. Paste your list of cards (Buy or Sell).
2. Get a unique link.
3. Send the link to a partner.
4. They paste their list.
5. See the matches!

## Deployment on Render
1. Create a new **Web Service** on Render.
2. Connect this repository.
3. Render should automatically detect Python.
4. If asked for a Build Command, use: `pip install -r requirements.txt`
5. If asked for a Start Command, use: `gunicorn app:app`
6. (Optional) For data persistence, add a PostgreSQL database and link it. The app checks for `DATABASE_URL`.
