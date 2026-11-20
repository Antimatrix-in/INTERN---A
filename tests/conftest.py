import pytest
import os
from datetime import datetime, timezone, timedelta
from app import create_app
from models import db, User, Assessment, Question

@pytest.fixture
def app():
    # Use testing config (defaults to isolated SQLite test database)
    app = create_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def admin_user_id(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin_test').first()
        if not admin:
            admin = User(
                user_id='AM-TEST-ADMIN',
                username='admin_test',
                email='admintest@example.com',
                full_name='Test Admin',
                role='ADMIN',
                is_active=True
            )
            admin.set_password('AdminPass123!')
            db.session.add(admin)
            db.session.commit()
        return admin.id

@pytest.fixture
def test_assessment_id(app, admin_user_id):
    with app.app_context():
        ass = Assessment.query.filter_by(code='AM-TEST-01').first()
        if not ass:
            ass = Assessment(
                code='AM-TEST-01',
                title='Software Engineering Assessment',
                description='Test assessment description',
                duration_minutes=30,
                pass_percentage=60.0,
                mcq_count=5,
                coding_count=2,
                is_active=True,
                created_by_id=admin_user_id
            )
            db.session.add(ass)
            db.session.commit()
            
            # Add sample question
            q = Question(
                assessment_id=ass.id,
                question_text='Which data structure operates on LIFO principle?',
                question_type='MCQ',
                options=[
                    {'id': 'A', 'text': 'Queue'},
                    {'id': 'B', 'text': 'Stack'},
                    {'id': 'C', 'text': 'Array'},
                    {'id': 'D', 'text': 'Tree'}
                ],
                correct_option='B',
                points=1.0,
                difficulty='EASY',
                category='Data Structures',
                is_active=True
            )
            db.session.add(q)
            db.session.commit()
        return ass.id
