import json
import re
import threading
import webbrowser
import os
import pickle
from datetime import datetime
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.utils import secure_filename

import numpy as np
from flask import Flask, jsonify, redirect, render_template, request, url_for


# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)

# ── Constants ────────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).parent / "data" / "children.json"
UPLOAD_FOLDER = Path(__file__).parent / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

PERIOD_OPTIONS = [
    ("6_months", "Last 6 Months"),
    ("last_month", "Last month"),
    ("last_week", "Last week"),
    ("today", "Today"),
]

FOOD_DATABASE = {
    "baby omelette":  {"Fat": 2.8, "Protein": 4.2, "Carbohydrates": 1.2,  "Calcium": 55,  "Iron": 0.7, "Vitamin D": 25},
    "omelette":       {"Fat": 2.5, "Protein": 3.8, "Carbohydrates": 1,    "Calcium": 42,  "Iron": 0.5, "Vitamin D": 20},
    "banana puree":   {"Carbohydrates": 12,         "Fiber": 1.5,          "Calcium": 6,   "Iron": 0.2},
    "baby porridge":  {"Fat": 1.5, "Protein": 3,   "Carbohydrates": 18,   "Fiber": 1.2,   "Calcium": 80,  "Iron": 1.1},
    "chicken puree":  {"Fat": 1.8, "Protein": 7.5, "Carbohydrates": 1,    "Iron": 0.6},
    "vegetable soup": {"Protein": 1.5,              "Carbohydrates": 8,    "Fiber": 2.2,   "Calcium": 35,  "Iron": 0.8},
    "avocado puree":  {"Fat": 5,   "Protein": 1,   "Carbohydrates": 4,    "Fiber": 2.8,   "Calcium": 8,   "Iron": 0.3},
    "salmon puree":   {"Fat": 3.5, "Protein": 6,   "Calcium": 18,         "Iron": 0.3,    "Vitamin D": 95},
    "yogurt":         {"Fat": 2,   "Protein": 4,   "Carbohydrates": 6,    "Calcium": 120, "Vitamin D": 35},
    "steak":          {"Fat": 4,   "Protein": 9,   "Iron": 1.2},
    "default":        {"Fat": 1.5, "Protein": 2.5, "Carbohydrates": 7,    "Fiber": 1,     "Calcium": 35,  "Iron": 0.4, "Vitamin D": 12},
}

# ── ML Model ─────────────────────────────────────────────────────────────────
basedir = os.path.dirname(__file__)
model_path = os.path.join(basedir, "model.pkl")

with open(model_path, "rb") as f:
    model = pickle.load(f)

# ── Default / seed data ───────────────────────────────────────────────────────
default_children = {
    "steve": {
        "id": "steve",
        "name": "Baby Steve",
        "age_months": 6,
        "avatar": "baby-steve.svg",
        "gender": "Male",
        "height": 67,
        "weight": 7.8,
        "bmi": 17.4,
        "prediction": "Normal",
        "prediction_note": (
            "Baby Steve is growing well! The summary shows that Steve's height "
            "and weight are steadily growing, while having a balanced nutritional "
            "intake. Keep up the great work!"
        ),
        "history": [
            {"month": "Dec 2025", "height": 63.2, "weight": 6.8},
            {"month": "Jan 2026", "height": 64.8, "weight": 7.2},
            {"month": "Feb 2026", "height": 66.1, "weight": 7.6},
            {"month": "Mar 2026", "height": 67.3, "weight": 7.9},
            {"month": "Apr 2026", "height": 68.4, "weight": 8.2},
            {"month": "May 2026", "height": 69.8, "weight": 8.6},
        ],
        "nutrition": [
            {"name": "Fat",           "intake": "10g / 15g",         "percent": 50, "remaining": "50% more"},
            {"name": "Protein",       "intake": "18g / 24g",         "percent": 75, "remaining": "25% more"},
            {"name": "Carbohydrates", "intake": "60g / 80g",         "percent": 75, "remaining": "25% more"},
            {"name": "Fiber",         "intake": "3g / 10g",          "percent": 30, "remaining": "70% more"},
            {"name": "Calcium",       "intake": "300mg / 600mg",     "percent": 50, "remaining": "50% more"},
            {"name": "Iron",          "intake": "4mg / 9mg",         "percent": 44, "remaining": "56% more"},
            {"name": "Vitamin D",     "intake": "200 IU / 400 IU",   "percent": 50, "remaining": "50% more"},
        ],
        "meals": ["Baby omelette"],
    }
}

# ── Persistence helpers ───────────────────────────────────────────────────────
def load_children():
    if DATA_FILE.exists():
        with DATA_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    save_children(default_children)
    return deepcopy(default_children)


def save_children(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_profile_picture(file, child_id):
    if not file or file.filename == "":
        return None

    if not allowed_file(file.filename):
        return None

    safe_name = secure_filename(file.filename)
    ext = safe_name.rsplit(".", 1)[1].lower()

    filename = f"{child_id}.{ext}"

    upload_path = app.config["UPLOAD_FOLDER"]
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = upload_path / filename

    for old_file in upload_path.glob(f"{child_id}.*"):
        old_file.unlink(missing_ok=True)

    file.save(file_path)

    return f"uploads/{filename}"


children = load_children()

# ── Child helpers ─────────────────────────────────────────────────────────────
def current_child(child_id):
    return children.get(child_id) or next(iter(children.values()))


def slugify_child_name(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "child"
    candidate, counter = slug, 2
    while candidate in children:
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate


def default_nutrition():
    return deepcopy(default_children["steve"]["nutrition"])


def empty_daily_nutrition():
    daily_nutrition = []
    for nutrient in default_nutrition():
        _, goal, unit = parse_intake(nutrient["intake"])
        daily_nutrition.append({
            "name":      nutrient["name"],
            "intake":    f"{format_amount(0, unit)} / {format_amount(goal, unit)}",
            "percent":   0,
            "remaining": "100% more",
        })
    return daily_nutrition


def ensure_daily_nutrition(child):
    today = datetime.now().strftime("%Y-%m-%d")
    if child.get("nutrition_date") == today:
        return False
    if "nutrition_date" not in child:
        child["nutrition_date"] = today
        return True
    child["nutrition"] = empty_daily_nutrition()
    child["nutrition_date"] = today
    return True

def split_age(months):
    months = int(months)
    years = months // 12
    remaining_months = months % 12
    return years, remaining_months


def build_new_child(name, age_months, height, weight, gender):
    child_id = slugify_child_name(name)
    bmi = round(weight / ((height / 100) ** 2), 1) if height and weight else 0
    return {
        "id":       child_id,
        "profile_picture": None,
        "name":     name,
        "age_months": age_months,
        "gender":   gender,
        "avatar":   "baby-steve.svg",
        "height":   height,
        "weight":   weight,
        "bmi":      bmi,
        "prediction":      "Unknown",
        "prediction_note": (
            f"{name} has been added to the dashboard. Keep updating height, "
            "weight, and meals so the growth summary stays accurate."
        ),
        "history": [{
            "month":  datetime.now().strftime("%b %Y"),
            "date":   datetime.now().strftime("%Y-%m-%d"),
            "height": round(height, 1),
            "weight": round(weight, 1),
        }],
        "nutrition":      empty_daily_nutrition(),
        "nutrition_date": datetime.now().strftime("%Y-%m-%d"),
        "meals":          [],
    }

# ── Chart / history helpers ───────────────────────────────────────────────────
def chart_y(value, value_min, value_max):
    top, bottom = 40, 280
    if value_max == value_min:
        return (top + bottom) / 2
    return bottom - ((value - value_min) / (value_max - value_min)) * (bottom - top)


def parse_history_date(item, child, index, history):
    if item.get("date"):
        return datetime.strptime(item["date"], "%Y-%m-%d")
    is_latest_current = (
        index == len(history) - 1
        and float(item.get("height", 0)) == float(child.get("height", 0))
        and float(item.get("weight", 0)) == float(child.get("weight", 0))
    )
    if is_latest_current:
        return datetime.now()
    try:
        return datetime.strptime(item.get("month", ""), "%b %Y")
    except ValueError:
        return datetime.now()


def history_for_period(child, period):
    history = child.get("history", [])

    if not history:
        return []

    period = period if period in dict(PERIOD_OPTIONS) else "6_months"

    now = datetime.now()

    starts = {
        "6_months":   now - timedelta(days=183),
        "last_month": now - timedelta(days=30),
        "last_week":  now - timedelta(days=7),
        "today":      now.replace(hour=0, minute=0, second=0, microsecond=0),
    }

    filtered = []

    for index, item in enumerate(history):

        item_date = parse_history_date(item, child, index, history)

        if item_date >= starts[period]:

            point = deepcopy(item)

            point["date"] = item_date.strftime("%Y-%m-%d")

            point["label"] = (
                item_date.strftime("%b %Y")
                if period == "6_months"
                else item_date.strftime("%b %d")
            )

            filtered.append(point)

    # ------------------------------
    # KEEP ONLY NEWEST ENTRY PER MONTH+YEAR
    # ------------------------------

    newest_per_month = {}

    filtered.sort(
        key=lambda x: datetime.strptime(
            x["date"],
            "%Y-%m-%d"
        )
    )

    for item in filtered:

        dt = datetime.strptime(
            item["date"],
            "%Y-%m-%d"
        )

        key = (dt.year, dt.month)

        newest_per_month[key] = item

    filtered = list(newest_per_month.values())

    # ------------------------------

    if not filtered:

        filtered = [{
            "month": now.strftime("%b %Y"),
            "date": now.strftime("%Y-%m-%d"),
            "label": "Today",
            "height": child.get("height", 0),
            "weight": child.get("weight", 0),
        }]

    return filtered[-6:]


def dashboard_child(child, period="6_months"):
    display_child = deepcopy(child)
    history = history_for_period(display_child, period)
    display_child["selected_period"] = period
    display_child["period_label"]    = dict(PERIOD_OPTIONS).get(period, "Last 6 Months")
    display_child["period_options"]  = PERIOD_OPTIONS
    if not history:
        display_child["chart_points"]      = []
        display_child["height_polyline"]   = ""
        display_child["weight_polyline"]   = ""
        return display_child

    x_min, x_max = 95, 685
    step = (x_max - x_min) / max(len(history) - 1, 1)

    # Dynamic ranges
    heights = [float(h["height"]) for h in history]
    weights = [float(h["weight"]) for h in history]

    height_min = min(heights) - 5
    height_max = max(heights) + 5

    weight_min = min(weights) - 1
    weight_max = max(weights) + 1

    points = []

    for index, item in enumerate(history):
        x = (x_min + x_max) / 2 if len(history) == 1 else x_min + (step * index)

        height_y = chart_y(
            float(item["height"]),
            height_min,
            height_max
        )

        weight_y = chart_y(
            float(item["weight"]),
            weight_min,
            weight_max
        )
        points.append({
            "month":        item.get("label") or item.get("month") or item.get("date"),
            "height":       item["height"],
            "weight":       item["weight"],
            "x":            round(x, 1),
            "height_y":     round(height_y, 1),
            "weight_y":     round(weight_y, 1),
            "height_point": f"{round(x, 1)},{round(height_y, 1)}",
            "weight_point": f"{round(x, 1)},{round(weight_y, 1)}",
        })

    display_child["chart_points"]    = points
    display_child["height_polyline"] = " ".join(p["height_point"] for p in points)
    display_child["weight_polyline"] = " ".join(p["weight_point"] for p in points)
    return display_child

# ── Nutrition helpers ─────────────────────────────────────────────────────────
def parse_intake(intake):
    match = re.match(r"\s*([\d.]+)\s*([A-Za-z ]+)\s*/\s*([\d.]+)\s*([A-Za-z ]+)\s*", intake)
    if not match:
        return 0, 1, ""
    return float(match.group(1)), float(match.group(3)), match.group(2).strip()


def format_amount(value, unit):
    rounded = round(value, 1)
    display_value = int(rounded) if rounded.is_integer() else rounded
    return f"{display_value} {unit}" if unit == "IU" else f"{display_value}{unit}"


def food_nutrition_for(meal):
    normalized = re.sub(r"[^a-z0-9]+", " ", meal.lower()).strip()
    for key, nutrition in FOOD_DATABASE.items():
        if key != "default" and key in normalized:
            return nutrition
    return FOOD_DATABASE["default"]


def update_nutrition_after_meal(child, meal):
    boost = food_nutrition_for(meal)
    for nutrient in child["nutrition"]:
        current, goal, unit = parse_intake(nutrient["intake"])
        current  = min(goal, current + float(boost.get(nutrient["name"], 0)))
        percent  = min(100, round((current / goal) * 100)) if goal else 0
        nutrient["intake"]    = f"{format_amount(current, unit)} / {format_amount(goal, unit)}"
        nutrient["percent"]   = percent
        nutrient["remaining"] = f"{100 - percent}% more"

# ── Static / informational pages ─────────────────────────────────────────────
@app.route("/")
@app.route("/index.html")
def home():
    return render_template("index.html")


@app.route("/parenting-guides.html")
@app.get("/parenting-guides")
def parenting_guides():
    return render_template("parenting-guides.html")


@app.route("/parenting-article-example.html")
def parenting_article():
    return render_template("parenting-article-example.html")


@app.route("/healthy-recipes.html")
@app.get("/healthy-recipes")
def healthy_recipes():
    return render_template("healthy-recipes.html")


@app.route("/forum.html")
@app.get("/forum")
def forum():
    return render_template("forum.html")


@app.route("/forum-example.html")
def forum_example():
    return render_template("forum-example.html")


@app.route("/stunting-prediction.html")
def stunting_prediction():
    data = load_children()

    children_list = list(data.values())

    for c in children_list:
        total = c.get("age_months", 0)
        years, months = split_age(total)
        c["age_years"] = years
        c["age_months_display"] = months

    return render_template(
        "stunting-prediction.html",
        children=children_list
    )


@app.route("/stunting-results.html")
def stunting_results():
    return render_template("stunting-results.html")


@app.post("/predict")
def predict():
    child_id = request.form.get("child_id")

    data = load_children()

    if child_id:
        child = data.get(child_id)

        if not child:
            return "Child not found", 404

    else:
        # Quick prediction mode
        child = {
            "name": "Quick Prediction Child"
        }

    gender_s = str(request.form["gender"])
    gender = 1 if gender_s == "laki-laki" else 2

    age_years = int(request.form.get("age_years", 0))
    age_months = int(request.form.get("age_months", 0))

    total_months = (age_years * 12) + age_months

    height_cm = float(request.form.get("height_cm", 0))
    weight_kg = float(request.form.get("weight_kg", 0))

    features = np.array([
        [gender, height_cm, total_months]
    ])

    prediction = model.predict(features)
    probability = model.predict_proba(features)

    pred_confidence = round(
        float(np.max(probability)) * 100,
        2
    )

    pred_label = prediction[0].lower().strip()

    if pred_label == "severely stunted":
        result = "Severely Stunted"

        recommendation = (
            "Please seek medical attention immediately. "
            "Consult a pediatrician or nutritionist "
            "for a thorough nutritional assessment "
            "and a stunting intervention plan."
        )

        prediction_note = (
            f"{child['name']} shows significant growth delays "
            "compared to children of the same age. "
            "Immediate professional medical consultation is strongly recommended."
        )

    elif pred_label == "stunted":
        result = "Stunted"

        recommendation = (
            "We recommend scheduling a nutritional "
            "check-up with a pediatrician as soon as possible. "
            "Early intervention with a balanced diet "
            "can significantly improve growth outcomes."
        )

        prediction_note = (
            f"{child['name']} may be experiencing slower growth "
            "than expected for their age. "
            "Improved nutrition and regular monitoring "
            "can help support healthier development."
        )

    elif pred_label == "tinggi":
        result = "Tall"

        recommendation = (
            "Your child's height is above average "
            "for their age, which is generally healthy. "
            "Continue providing balanced nutrition "
            "and regular growth monitoring."
        )

        prediction_note = (
            f"{child['name']}'s height is above average "
            "for their age group. Growth appears healthy "
            "and should continue to be monitored regularly."
        )

    elif pred_label == "normal":
        result = "Normal"

        recommendation = (
            "Keep up the great work! Continue providing "
            "a balanced nutritious diet and regular "
            "health check-ups to support healthy development."
        )

        prediction_note = (
            f"{child['name']} is growing well! "
            "Height and weight are progressing steadily "
            "with balanced nutritional intake."
        )

    else:
        result = "Unknown"

        recommendation = (
            "An unexpected result was returned. "
            "Please double-check the input data."
        )

        prediction_note = (
            "Prediction could not be generated properly."
        )

    if total_months >= 24:
        height_m = height_cm / 100

        bmi = round(
            weight_kg / (height_m ** 2),
            2
        )

        if bmi < 18.5:
            bmi_result = "Underweight"

        elif bmi < 25:
            bmi_result = "Normal weight"

        elif bmi < 30:
            bmi_result = "Overweight"

        else:
            bmi_result = "Obese"

    else:
        bmi = "-"
        bmi_result = (
            "Not available — child is under 24 months"
        )

    child["prediction"] = result
    child["prediction_note"] = prediction_note

    save_children(data)

    return render_template(
        "stunting-results.html",
        child=child,
        age_years=age_years,
        age_months=age_months,
        total_months=total_months,
        bmi=bmi,
        bmi_result=bmi_result,
        gender_s=gender_s,
        height_cm=height_cm,
        weight_kg=weight_kg,
        result=result,
        confidence=pred_confidence,
        recommendation=recommendation,
    )

# ── Growth dashboard (UI) ─────────────────────────────────────────────────────
@app.route("/growth-dashboard.html")
def select_child():
    data = load_children()

    return render_template(
        "select-child.html",
        children=data.values()
    )


@app.post("/growth-dashboard")
def confirm_child():
    child_id = request.form.get("child_id", "steve")
    return redirect(url_for("dashboard", child_id=child_id))


@app.post("/growth-dashboard/add-child")
def add_child():
    name = request.form.get("name", "").strip()
    age_months = request.form.get("age_months", type=int)
    gender = request.form.get("gender")
    height = request.form.get("height", type=float)
    weight = request.form.get("weight", type=float)

    if not name or age_months is None or height is None or weight is None or not gender:
        return redirect(url_for("select_child"))

    child = build_new_child(name, age_months, height, weight, gender)

    # save uploaded image
    file = request.files.get("profile_picture")

    picture_path = save_profile_picture(file, child["id"])

    if picture_path:
        child["profile_picture"] = picture_path

    children[child["id"]] = child

    save_children(children)

    return redirect(url_for("dashboard", child_id=child["id"]))

@app.route('/growth-dashboard/delete_child/<child_id>', methods=['POST'])
def delete_child(child_id):

    data = load_children()

    child = data.get(child_id)

    if child:

        # delete uploaded picture if exists
        if child.get("profile_picture"):

            file_path = Path(app.static_folder) / child["profile_picture"]

            if file_path.exists():
                file_path.unlink()

        # remove child from dictionary
        del data[child_id]

        save_children(data)

        # keep global variable synced
        global children
        children = data

    return redirect(url_for('select_child'))

@app.route("/growth-dashboard/<child_id>")
def dashboard(child_id):
    period         = request.args.get("range", "6_months")
    selected_child = current_child(child_id)
    if ensure_daily_nutrition(selected_child):
        save_children(children)
    child = dashboard_child(selected_child, period)
    return render_template("dashboard.html", child=child)


@app.route("/growth-dashboard/<child_id>/update", methods=["GET", "POST"])
def update_data(child_id):
    child = current_child(child_id)
    if request.method == "POST":
        height = request.form.get("height", type=float)
        weight = request.form.get("weight", type=float)

        file = request.files.get("profile_picture")

        picture_path = save_profile_picture(file, child["id"])

        if picture_path:
            child["profile_picture"] = picture_path
        if height:
            child["height"] = height
        if weight:
            child["weight"] = weight
        if height and weight:
            child["bmi"] = round(weight / ((height / 100) ** 2), 1)
            child["history"].append({
                "month":  datetime.now().strftime("%b %Y"),
                "date":   datetime.now().strftime("%Y-%m-%d"),
                "height": round(height, 1),
                "weight": round(weight, 1),
            })
        save_children(children)
        return redirect(url_for("dashboard", child_id=child["id"]))
    return render_template("update_data.html", child=child)


@app.route("/growth-dashboard/<child_id>/meal", methods=["GET", "POST"])
def input_meal(child_id):
    child = current_child(child_id)
    if ensure_daily_nutrition(child):
        save_children(children)
    if request.method == "POST":
        meal = request.form.get("meal", "").strip()
        if meal:
            child["meals"].append(meal)
            update_nutrition_after_meal(child, meal)
            save_children(children)
        return redirect(url_for("dashboard", child_id=child["id"]))
    food_names = [name.title() for name in FOOD_DATABASE if name != "default"]
    return render_template("input-meal.html", child=child, food_names=food_names)

# ── REST API ──────────────────────────────────────────────────────────────────
@app.get("/api/children")
def api_children():
    return jsonify([
        {"id": c["id"], "name": c["name"], "age_months": c["age_months"]}
        for c in children.values()
    ])


@app.get("/api/children/<child_id>/growth")
def api_growth(child_id):
    child = current_child(child_id)
    if ensure_daily_nutrition(child):
        save_children(children)
    return jsonify(deepcopy(child))


@app.route("/api/children/<child_id>/growth", methods=["PUT", "PATCH"])
def api_update_growth(child_id):
    child   = current_child(child_id)
    payload = request.get_json(silent=True) or {}
    height  = payload.get("height")
    weight  = payload.get("weight")
    if height is not None:
        child["height"] = float(height)
    if weight is not None:
        child["weight"] = float(weight)
    if height is not None and weight is not None:
        child["bmi"] = round(child["weight"] / ((child["height"] / 100) ** 2), 1)
        child["history"].append({
            "month":  datetime.now().strftime("%b %Y"),
            "date":   datetime.now().strftime("%Y-%m-%d"),
            "height": round(child["height"], 1),
            "weight": round(child["weight"], 1),
        })
    save_children(children)
    return jsonify(deepcopy(child))


@app.post("/api/children")
def api_add_child():
    payload    = request.get_json(silent=True) or {}

    name       = str(payload.get("name", "")).strip()
    age_months = payload.get("age_months")
    gender     = payload.get("gender")
    height     = payload.get("height")
    weight     = payload.get("weight")

    if not name or age_months is None or height is None or weight is None or not gender:
        return jsonify({
            "error": "name, age_months, gender, height, and weight are required"
        }), 400

    child = build_new_child(
        name,
        int(age_months),
        float(height),
        float(weight),
        gender
    )

    children[child["id"]] = child
    save_children(children)

    return jsonify(deepcopy(child)), 201


@app.post("/api/children/<child_id>/meal")
def api_add_meal(child_id):
    child = current_child(child_id)
    if ensure_daily_nutrition(child):
        save_children(children)
    payload = request.get_json(silent=True) or {}
    meal    = str(payload.get("meal", "")).strip()
    if not meal:
        return jsonify({"error": "meal is required"}), 400
    child["meals"].append(meal)
    update_nutrition_after_meal(child, meal)
    save_children(children)
    return jsonify({"message": "meal saved", "meals": child["meals"]}), 201


# ── REST API: stunting prediction ─────────────────────────────────────────────
@app.post("/api/predict")
def api_predict():
    """JSON endpoint — same logic as the form-based /predict route."""
    payload      = request.get_json(silent=True) or {}
    gender_s     = str(payload.get("gender", "")).lower()
    gender = 1 if gender_s == "Male" else 2
    age_years    = int(payload.form.get("age_years", 0))
    age_months_v = int(payload.form.get("age_months", 0))
    total_months = (age_years * 12) + age_months_v
    height_cm    = float(payload.get("height_cm", 0))
    weight_kg    = float(payload.get("weight_kg", 0))

    if not height_cm or not total_months:
        return jsonify({"error": "gender, age_years/age_months, height_cm, and weight_kg are required"}), 400

    features        = np.array([[gender, height_cm, total_months]])
    prediction      = model.predict(features)
    probability     = model.predict_proba(features)
    pred_confidence = round(float(np.max(probability)) * 100, 2)

    if total_months >= 24:
        bmi        = round(weight_kg / ((height_cm / 100) ** 2), 2)
        bmi_result = (
            "Underweight" if bmi < 18.5
            else "Normal weight" if bmi < 25
            else "Overweight" if bmi < 30
            else "Obese"
        )
    else:
        bmi        = None
        bmi_result = "Not available — child is under 24 months"

    return jsonify({
        "prediction":    prediction[0],
        "confidence":    pred_confidence,
        "bmi":           bmi,
        "bmi_result":    bmi_result,
        "total_months":  total_months,
    })

# ── Dev server ────────────────────────────────────────────────────────────────
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.25, open_browser).start()
    app.run(debug=True)