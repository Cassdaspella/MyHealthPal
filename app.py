from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import date
import requests


app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

# Extensions initialization
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)
    goal = db.Column(db.String(50), nullable=True)
    calorie_intake = db.Column(db.Float, nullable=True)
    name = db.Column(db.String(150), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(50), nullable=True)
    birthday = db.Column(db.Date, nullable=True)
    activity_level = db.Column(db.String(150), nullable=True)
    health_concerns = db.Column(db.String(500), nullable=True)

# BMR Calculator Route 
def calculate_bmr(weight, height, age, gender, activity_level):
    multipliers = {
        'extra-active': 1.9,
        'very-active': 1.725,
        'lightly-active': 1.375,
        'moderately-active': 1.55,
        'sedentary': 1.2
    }

    if gender == "male":
        bmr = 13.397 * weight + 4.799 * height - 5.677 * age + 88.362
    else:
        bmr = 9.247 * weight + 3.098 * height - 4.330 * age + 447.593

    activity_multiplier = multipliers.get(activity_level, 1.2)
    return bmr * activity_multiplier

# Route to handle BMR calculation
@app.route('/calculate_bmr', methods=['POST'])
def calculate_bmr_route():
    data = request.get_json()

    user_weight = float(data['weight'])
    user_height = float(data['height'])
    user_age = int(data['age'])
    user_gender = data['gender']
    activity_level = data['activityLevel']

    bmr = calculate_bmr(user_weight, user_height, user_age, user_gender, activity_level)

    return {'bmr': bmr}

def calculate_calories(goal, user):
    if goal == 'maintenance':
        return user.calorie_intake
    elif goal == 'mild_weight_loss':
        return user.calorie_intake - 250
    elif goal == 'weight_loss':
        return user.calorie_intake - 500
    elif goal == 'extreme_weight_loss':
        return user.calorie_intake - 1000
    elif goal == 'mild_weight_gain':
        return user.calorie_intake + 250
    elif goal == 'weight_gain':
        return user.calorie_intake + 500
    elif goal == 'extreme_weight_gain':
        return user.calorie_intake + 1000
    else:
        return None  # Handle invalid goal types

# Routes
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        weight = float(request.form.get("weight"))  # Convert to float
        height = float(request.form.get("height"))  # Convert to float
        goal = request.form.get("goal")  # Use the request object to get the goal
        age = int(request.form.get('age'))
        gender = request.form.get('gender')
        activity_level = request.form.get('activity-level')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        if goal == 'bulk':
            calories = (10 * float(weight) + 6.25 * float(height) - 5 * 25 + 5) * 1.1  # Example formula
        else:  # goal == 'cut'
            calories = (10 * float(weight) + 6.25 * float(height) - 5 * 25 + 5) * 0.9  # Example formula

        new_user = User(username=username, password=hashed_password, weight=weight, height=height, goal=goal,
                        calorie_intake=calories, name=None, age=age, gender=gender, birthday=None,
                        activity_level=activity_level, health_concerns=None)
        db.session.add(new_user)
        db.session.commit()

        flash(f'Registration successful! Your daily calorie target is {calories:.0f} kcal.', 'success')
        login_user(new_user)  # Automatically log in the new user
        return redirect(url_for('profile'))

    return render_template("register.html")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/food_list/', defaults={'goal': None}, methods=['GET'])
@app.route('/food_list/<goal>', methods=['GET'])
def food_list(goal):
    # Map user goals to Spoonacular diet options
    diet_map = {
        'bulking': 'Whole30',  # This is just a placeholder. You should choose an appropriate diet type from Spoonacular's options.
        'cutting': 'Ketogenic',
        'maintenance': 'Balanced'
    }

    if goal:
        diet = diet_map.get(goal)
        
        # Avoid exposing your API key directly in the code. Consider using environment variables.
        api_key = "a5e830b7c7764e80aab845f83c02feda"

        # Construct the API URL
        url = f"https://api.spoonacular.com/recipes/complexSearch?diet={diet}&apiKey={api_key}"
        
        response = requests.get(url)
        data = response.json()
        
        recipes = data.get('results', [])
    else:
        recipes = []

    return render_template('food_list.html', recipes=recipes, goal=goal)


@app.route('/calculations')
def calculations():
    return render_template('calculations.html')

@app.route('/exercise')
def exercise():
    return render_template('exercise.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login failed. Check your login details and try again.', 'danger')
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/home")
@login_required
def home():
    return render_template("index.html")

@app.route('/questionnaire', methods=['GET', 'POST'])
@login_required
def questionnaire():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.age = request.form.get('age')
        current_user.gender = request.form.get('gender')
        
        # Convert the birthday string to a date object
        birthday_str = request.form.get('birthday')
        year, month, day = map(int, birthday_str.split('-'))
        current_user.birthday = date(year, month, day)
        
        current_user.height = request.form.get('height')
        current_user.weight = request.form.get('weight')  # Note: This field already exists
        current_user.activity_level = request.form.get('activity-level')
        current_user.health_concerns = request.form.get('health-concerns')

        db.session.commit()

        flash('Questionnaire data saved!', 'success')
        return redirect(url_for('profile'))
    return render_template('questionnaire.html')


@app.route("/profile")
@login_required
def profile():
    calorie_intake = current_user.calorie_intake

    # Additional calorie outputs
    maintenance_calories = calculate_calories("maintenance", current_user)
    mild_weight_loss = calculate_calories("mild_weight_loss", current_user)
    weight_loss = calculate_calories("weight_loss", current_user)
    extreme_weight_loss = calculate_calories("extreme_weight_loss", current_user)
    mild_weight_gain = calculate_calories("mild_weight_gain", current_user)
    weight_gain = calculate_calories("weight_gain", current_user)
    extreme_weight_gain = calculate_calories("extreme_weight_gain", current_user)

    return render_template(
        "profile.html",
        calorie_intake=calorie_intake,
        maintenance_calories=maintenance_calories,
        mild_weight_loss=mild_weight_loss,
        weight_loss=weight_loss,
        extreme_weight_loss=extreme_weight_loss,
        mild_weight_gain=mild_weight_gain,
        weight_gain=weight_gain,
        extreme_weight_gain=extreme_weight_gain
    )

@app.route('/handle_contact', methods=['POST'])
def handle_contact():
    # Logic for handling the form data, like saving it to a database or sending an email.
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    # For now, let's print the received data (this is just for demonstration purposes)
    print(name, email, message)
    
    flash('Your message has been sent successfully!', 'success')
    return redirect(url_for('contact'))


# Helper functions
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

migrate = Migrate(app, db)
