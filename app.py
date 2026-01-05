from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import json
from models import db, Trade
import card_data
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)

# Database Configuration
# Render sets DATABASE_URL for Postgres. We use sqlite for local dev.
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Scheduler Setup
scheduler = BackgroundScheduler()

def scheduled_update():
    """Wrapper to run update_card_database with app context."""
    with app.app_context():
        card_data.update_card_database(app)

scheduler.add_job(func=scheduled_update, trigger="interval", weeks=1)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# Create tables before first request
with app.app_context():
    db.create_all()
    # Pre-load card data (checks DB, updates if stale/missing)
    card_data.load_card_data(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/validate', methods=['POST'])
def validate():
    data = request.get_json()
    raw_list = data.get('cards', '')
    # Pass app just in case it needs to load data (though it should be loaded on start)
    valid, unknown = card_data.validate_card_list(raw_list, app)
    return jsonify({'valid': valid, 'unknown': unknown})

@app.route('/create', methods=['POST'])
def create_trade():
    mode = request.form.get('mode') # 'buy' or 'sell'
    raw_list = request.form.get('card_list')

    if not mode or not raw_list:
        return "Missing data", 400

    valid, _ = card_data.validate_card_list(raw_list, app)

    if not valid:
        return "No valid cards found", 400

    new_trade = Trade(
        creator_mode=mode,
        creator_cards=json.dumps(valid)
    )

    db.session.add(new_trade)
    db.session.commit()

    return redirect(url_for('view_trade', trade_id=new_trade.id))

@app.route('/trade/<trade_id>', methods=['GET', 'POST'])
def view_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)

    if request.method == 'POST':
        # User 2 submitting their list
        raw_list = request.form.get('partner_card_list')
        if raw_list:
            valid, _ = card_data.validate_card_list(raw_list, app)
            trade.partner_cards = json.dumps(valid)
            db.session.commit()
            return redirect(url_for('view_trade', trade_id=trade_id))

    creator_cards = json.loads(trade.creator_cards)
    partner_cards = json.loads(trade.partner_cards) if trade.partner_cards else []

    matches = []
    if partner_cards:
        set_creator = set(creator_cards)
        set_partner = set(partner_cards)
        matches = list(set_creator.intersection(set_partner))
        matches.sort()

    return render_template('trade.html', trade=trade, creator_cards=creator_cards, partner_cards=partner_cards, matches=matches)

if __name__ == '__main__':
    app.run(debug=True)
