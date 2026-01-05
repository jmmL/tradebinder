import unittest
import json
import card_data
from app import app, db
from models import Trade

class BasicTests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
            # Mock card data for testing to avoid network call
            card_data.CARD_LIST = {"Lightning Bolt", "Forest", "Black Lotus"}

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'MTG Trade Matcher', response.data)

    def test_validate_api_valid(self):
        response = self.app.post('/api/validate',
                                 json={'cards': 'Lightning Bolt\nForest'})
        data = response.get_json()
        self.assertEqual(len(data['valid']), 2)
        self.assertEqual(len(data['unknown']), 0)

    def test_validate_api_invalid(self):
        response = self.app.post('/api/validate',
                                 json={'cards': 'Pikachu\nLightning Bolt'})
        data = response.get_json()
        self.assertEqual(len(data['valid']), 1)
        self.assertEqual(len(data['unknown']), 1)
        self.assertIn('Pikachu', data['unknown'])

    def test_create_trade(self):
        response = self.app.post('/create', data={
            'mode': 'sell',
            'card_list': 'Lightning Bolt'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Trade Match', response.data)
        # Check database
        with app.app_context():
            trade = Trade.query.first()
            self.assertIsNotNone(trade)
            self.assertEqual(trade.creator_mode, 'sell')

if __name__ == "__main__":
    unittest.main()
