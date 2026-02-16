from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import joblib
import numpy as np
import os
from functools import wraps

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'titanic-survey-2026')

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')   

ALLOWED_ORIGINS = [
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'null',
    os.environ.get('FRONTEND_URL', ''),
]
CORS(app, supports_credentials=True, origins=[o for o in ALLOWED_ORIGINS if o])

db            = SQLAlchemy(app)
login_manager = LoginManager(app)


class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False)
    predictions   = db.relationship('Prediction', backref='user', lazy=True, cascade='all, delete-orphan')

    def is_active(self):        return True
    def is_authenticated(self): return True
    def is_anonymous(self):     return False
    def get_id(self):           return str(self.id)

class Prediction(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pclass      = db.Column(db.Integer)
    sex         = db.Column(db.String(10))
    age         = db.Column(db.Float)
    sibsp       = db.Column(db.Integer)
    parch       = db.Column(db.Integer)
    fare        = db.Column(db.Float)
    embarked    = db.Column(db.String(5))
    result      = db.Column(db.String(20))
    probability = db.Column(db.Float)
    timestamp   = db.Column(db.DateTime, default=db.func.now())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

MODEL_PATH   = os.path.join(os.path.dirname(__file__), 'models', 'titanic_model.pkl')
ENCODER_PATH = os.path.join(os.path.dirname(__file__), 'models', 'sex_encoder.pkl')
model        = None
sex_encoder  = None

def load_model():
    global model, sex_encoder
    try:
        model       = joblib.load(MODEL_PATH)
        sex_encoder = joblib.load(ENCODER_PATH)
        print(' Model loaded successfully')
    except Exception as e:
        print(f' Model not found: {e}. Run training/train_model.py first.')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ['username', 'email', 'password']):
        return jsonify({'error': 'All fields required'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    user = User(
        username      = data['username'],
        email         = data['email'],
        password_hash = generate_password_hash(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({'message': 'Registered successfully', 'username': user.username}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
        admin = User.query.filter_by(username=ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username      = ADMIN_USERNAME,
                email         = 'admin@titanicsurvey.com',
                password_hash = generate_password_hash(ADMIN_PASSWORD),
                is_admin      = True
            )
            db.session.add(admin)
            db.session.commit()
        login_user(admin)
        return jsonify({'message': 'Admin logged in', 'username': admin.username, 'is_admin': True})

    user = User.query.filter_by(username=data.get('username')).first()
    if user and check_password_hash(user.password_hash, data.get('password', '')):
        login_user(user)
        return jsonify({'message': 'Logged in', 'username': user.username, 'is_admin': user.is_admin})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'})

@app.route('/api/status', methods=['GET'])
def status():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username, 'is_admin': current_user.is_admin})
    return jsonify({'authenticated': False})


@app.route('/api/predict', methods=['POST'])
@login_required
def predict():
    if model is None:
        return jsonify({'error': 'Model not loaded. Run train_model.py first.'}), 503
    data = request.get_json()
    try:
        sex_encoded  = sex_encoder.transform([data['sex']])[0]
        embarked_map = {'S': 0, 'C': 1, 'Q': 2}
        features = np.array([[
            int(data['pclass']),
            sex_encoded,
            float(data['age']),
            int(data['sibsp']),
            int(data['parch']),
            float(data['fare']),
            embarked_map.get(data.get('embarked', 'S'), 0)
        ]])
        prob   = model.predict_proba(features)[0][1]
        result = 'Survived' if prob >= 0.5 else 'Did Not Survive'
        prediction = Prediction(
            user_id=current_user.id, pclass=data['pclass'],
            sex=data['sex'], age=data['age'], sibsp=data['sibsp'],
            parch=data['parch'], fare=data['fare'],
            embarked=data.get('embarked', 'S'),
            result=result, probability=round(float(prob), 4)
        )
        db.session.add(prediction)
        db.session.commit()
        return jsonify({'result': result, 'probability': round(float(prob) * 100, 1)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/history', methods=['GET'])
@login_required
def history():
    preds = Prediction.query.filter_by(user_id=current_user.id)\
        .order_by(Prediction.timestamp.desc()).limit(10).all()
    return jsonify([{
        'id':          p.id,
        'pclass':      p.pclass,
        'sex':         p.sex,
        'age':         p.age,
        'result':      p.result,
        'probability': round(p.probability * 100, 1),
        'timestamp':   p.timestamp.strftime('%b %d, %Y %H:%M') if p.timestamp else 'N/A'
    } for p in preds])


@app.route('/api/admin/stats', methods=['GET'])
@login_required
@admin_required
def admin_stats():
    total_users       = User.query.filter_by(is_admin=False).count()
    total_predictions = Prediction.query.count()
    survived_count    = Prediction.query.filter_by(result='Survived').count()
    survival_rate     = round((survived_count / total_predictions * 100), 1) if total_predictions else 0
    return jsonify({
        'total_users':       total_users,
        'total_predictions': total_predictions,
        'survived':          survived_count,
        'not_survived':      total_predictions - survived_count,
        'survival_rate':     survival_rate
    })

@app.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_users():
    users = User.query.filter_by(is_admin=False).order_by(User.id.desc()).all()
    return jsonify([{
        'id':               u.id,
        'username':         u.username,
        'email':            u.email,
        'prediction_count': len(u.predictions)
    } for u in users])

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        return jsonify({'error': 'Cannot delete admin'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'User {user.username} deleted'})

@app.route('/api/admin/predictions', methods=['GET'])
@login_required
@admin_required
def admin_predictions():
    preds = Prediction.query.order_by(Prediction.timestamp.desc()).limit(50).all()
    return jsonify([{
        'id':          p.id,
        'username':    p.user.username,
        'pclass':      p.pclass,
        'sex':         p.sex,
        'age':         p.age,
        'result':      p.result,
        'probability': round(p.probability * 100, 1),
        'timestamp':   p.timestamp.strftime('%b %d, %Y %H:%M') if p.timestamp else 'N/A'
    } for p in preds])

@app.route('/api/admin/predictions/<int:pred_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_prediction(pred_id):
    pred = Prediction.query.get_or_404(pred_id)
    db.session.delete(pred)
    db.session.commit()
    return jsonify({'message': 'Prediction deleted'})

@app.route('/api/admin/predictions/clear', methods=['DELETE'])
@login_required
@admin_required
def admin_clear_predictions():
    Prediction.query.delete()
    db.session.commit()
    return jsonify({'message': 'All predictions cleared'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        load_model()
    app.run(debug=True, port=5000)

with app.app_context():
    db.create_all()
    load_model()