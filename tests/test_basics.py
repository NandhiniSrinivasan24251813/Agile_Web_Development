import unittest
from app import app, db
from models import User
from datetime import datetime

class BasicTests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            db.create_all()
            user = User(username='testuser', email='test@example.com', created_at=datetime.now())
            user.set_password('testpass')  # make sure this method exists
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_login_success(self):
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Logged in successfully!', response.data)

    def test_login_failure(self):
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password', response.data)
    def test_signup_success(self):
        response = self.client.post('/signup', data={
            'username': 'newuser',
            'email': 'newuser@yopmail.com',
            'password': 'newpass123',
            'confirm_password': 'newpass123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'ccount created successfully! Welcome email and otp sent.', response.data) 

        # Optionally, check user exists in DB
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)
    def test_logout(self):
    # First, log in
        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        }, follow_redirects=True)

        # Now logout
        response = self.client.get('/logout', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You have been logged out', response.data)
    def test_signup_failure_username_exists(self):
    # Create a user first to cause username duplicate error
        with app.app_context():
            user = User(username='existinguser', email='existing@yopmail.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()

        response = self.client.post('/signup', data={
            'username': 'existinguser',
            'email': 'newemail@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'mobile_number': '1234567890'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Username already exists', response.data)
    def test_signup_failure_email_exists(self):
    # Create a user first to cause email duplicate error
        with app.app_context():
            user = User(username='uniqueuser', email='existingemail@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()

        response = self.client.post('/signup', data={
            'username': 'newuser',
            'email': 'existingemail@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'mobile_number': '1234567890'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Email already exists', response.data)






if __name__ == '__main__':
    unittest.main()
