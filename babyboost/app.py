import json
import re
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for


app = Flask(__name__)
DATA_FILE = Path(__file__).parent / "data" / "children.json"
PERIOD_OPTIONS = [
    ("6_months", "Last 6 Months"),
    ("last_month", "Last month"),
    ("last_week", "Last week"),
    ("today", "Today"),
]
FOOD_DATABASE = {
    "baby omelette": {"Fat": 2.8, "Protein": 4.2, "Carbohydrates": 1.2, "Calcium": 55, "Iron": 0.7, "Vitamin D": 25},
    "omelette": {"Fat": 2.5, "Protein": 3.8, "Carbohydrates": 1, "Calcium": 42, "Iron": 0.5, "Vitamin D": 20},
    "banana puree": {"Carbohydrates": 12, "Fiber": 1.5, "Calcium": 6, "Iron": 0.2},
    "baby porridge": {"Fat": 1.5, "Protein": 3, "Carbohydrates": 18, "Fiber": 1.2, "Calcium": 80, "Iron": 1.1},
    "chicken puree": {"Fat": 1.8, "Protein": 7.5, "Carbohydrates": 1, "Iron": 0.6},
    "vegetable soup": {"Protein": 1.5, "Carbohydrates": 8, "Fiber": 2.2, "Calcium": 35, "Iron": 0.8},
    "avocado puree": {"Fat": 5, "Protein": 1, "Carbohydrates": 4, "Fiber": 2.8, "Calcium": 8, "Iron": 0.3},
    "salmon puree": {"Fat": 3.5, "Protein": 6, "Calcium": 18, "Iron": 0.3, "Vitamin D": 95},
    "yogurt": {"Fat": 2, "Protein": 4, "Carbohydrates": 6, "Calcium": 120, "Vitamin D": 35},
    "steak": {"Fat": 4, "Protein": 9, "Iron": 1.2},
    "default": {"Fat": 1.5, "Protein": 2.5, "Carbohydrates": 7, "Fiber": 1, "Calcium": 35, "Iron": 0.4, "Vitamin D": 12},
}


default_children = {
    "steve": {
        "id": "steve",
        "name": "Baby Steve",
        "age": "6 Months Old",
        "avatar": "baby-steve.svg",
        "height": 67,
        "weight": 7.8,
        "bmi": 17.4,
        "prediction": "Healthy",
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
            {"name": "Fat", "intake": "10g / 15g", "percent": 50, "remaining": "50% more"},
            {"name": "Protein", "intake": "18g / 24g", "percent": 75, "remaining": "25% more"},
            {"name": "Carbohydrates", "intake": "60g / 80g", "percent": 75, "remaining": "25% more"},
            {"name": "Fiber", "intake": "3g / 10g", "percent": 30, "remaining": "70% more"},
            {"name": "Calcium", "intake": "300mg / 600mg", "percent": 50, "remaining": "50% more"},
            {"name": "Iron", "intake": "4mg / 9mg", "percent": 44, "remaining": "56% more"},
            {"name": "Vitamin D", "intake": "200 IU / 400 IU", "percent": 50, "remaining": "50% more"},
        ],
        "meals": ["Baby omelette"],
    }
}


def load_children():
    if DATA_FILE.exists():
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    save_children(default_children)
    return deepcopy(default_children)


def save_children(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


children = load_children()


def current_child(child_id):
    return children.get(child_id) or next(iter(children.values()))


def slugify_child_name(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "child"
    candidate = slug
    counter = 2
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
        daily_nutrition.append(
            {
                "name": nutrient["name"],
                "intake": f"{format_amount(0, unit)} / {format_amount(goal, unit)}",
                "percent": 0,
                "remaining": "100% more",
            }
        )
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


def build_new_child(name, age_months, height, weight):
    child_id = slugify_child_name(name)
    bmi = round(weight / ((height / 100) ** 2), 1) if height and weight else 0
    return {
        "id": child_id,
        "name": name,
        "age": f"{age_months} Months Old",
        "avatar": "baby-steve.svg",
        "height": height,
        "weight": weight,
        "bmi": bmi,
        "prediction": "Healthy",
        "prediction_note": (
            f"{name} has been added to the dashboard. Keep updating height, "
            "weight, and meals so the growth summary stays accurate."
        ),
        "history": [
            {
                "month": datetime.now().strftime("%b %Y"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "height": round(height, 1),
                "weight": round(weight, 1),
            }
        ],
        "nutrition": empty_daily_nutrition(),
        "nutrition_date": datetime.now().strftime("%Y-%m-%d"),
        "meals": [],
    }


def chart_y(value, value_min, value_max):
    top = 40
    bottom = 280
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
        "6_months": now - timedelta(days=183),
        "last_month": now - timedelta(days=30),
        "last_week": now - timedelta(days=7),
        "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
    }

    filtered = []
    for index, item in enumerate(history):
        item_date = parse_history_date(item, child, index, history)
        if item_date >= starts[period]:
            point = deepcopy(item)
            point["date"] = item_date.strftime("%Y-%m-%d")
            point["label"] = item_date.strftime("%b %Y") if period == "6_months" else item_date.strftime("%b %d")
            filtered.append(point)

    if not filtered:
        filtered = [
            {
                "month": now.strftime("%b %Y"),
                "date": now.strftime("%Y-%m-%d"),
                "label": "Today",
                "height": child.get("height", 0),
                "weight": child.get("weight", 0),
            }
        ]

    return filtered[-6:]


def dashboard_child(child, period="6_months"):
    display_child = deepcopy(child)
    history = history_for_period(display_child, period)
    display_child["selected_period"] = period
    display_child["period_label"] = dict(PERIOD_OPTIONS).get(period, "Last 6 Months")
    display_child["period_options"] = PERIOD_OPTIONS
    if not history:
        display_child["chart_points"] = []
        display_child["height_polyline"] = ""
        display_child["weight_polyline"] = ""
        return display_child

    x_min = 95
    x_max = 685
    step = (x_max - x_min) / max(len(history) - 1, 1)
    points = []
    for index, item in enumerate(history):
        x = (x_min + x_max) / 2 if len(history) == 1 else x_min + (step * index)
        height_y = chart_y(float(item["height"]), 40, 80)
        weight_y = chart_y(float(item["weight"]), 4, 12)
        point = {
            "month": item.get("label") or item.get("month") or item.get("date"),
            "height": item["height"],
            "weight": item["weight"],
            "x": round(x, 1),
            "height_y": round(height_y, 1),
            "weight_y": round(weight_y, 1),
            "height_point": f"{round(x, 1)},{round(height_y, 1)}",
            "weight_point": f"{round(x, 1)},{round(weight_y, 1)}",
        }
        points.append(point)

    display_child["chart_points"] = points
    display_child["height_polyline"] = " ".join(point["height_point"] for point in points)
    display_child["weight_polyline"] = " ".join(point["weight_point"] for point in points)
    return display_child


def parse_intake(intake):
    match = re.match(r"\s*([\d.]+)\s*([A-Za-z ]+)\s*/\s*([\d.]+)\s*([A-Za-z ]+)\s*", intake)
    if not match:
        return 0, 1, ""
    current = float(match.group(1))
    unit = match.group(2).strip()
    goal = float(match.group(3))
    return current, goal, unit


def format_amount(value, unit):
    rounded = round(value, 1)
    display_value = int(rounded) if rounded.is_integer() else rounded
    if unit == "IU":
        return f"{display_value} {unit}"
    return f"{display_value}{unit}"


def food_nutrition_for(meal):
    normalized = re.sub(r"[^a-z0-9]+", " ", meal.lower()).strip()
    for key, nutrition in FOOD_DATABASE.items():
        if key != "default" and key in normalized:
            return nutrition
    return FOOD_DATABASE["default"]


def update_nutrition_after_meal(child, meal):
    nutrition_boost = food_nutrition_for(meal)
    for nutrient in child["nutrition"]:
        current, goal, unit = parse_intake(nutrient["intake"])
        current = min(goal, current + float(nutrition_boost.get(nutrient["name"], 0)))
        percent = min(100, round((current / goal) * 100)) if goal else 0
        nutrient["intake"] = f"{format_amount(current, unit)} / {format_amount(goal, unit)}"
        nutrient["percent"] = percent
        nutrient["remaining"] = f"{100 - percent}% more"


@app.route("/")
def home():
    return redirect(url_for("select_child"))


@app.get("/home")
def home_page():
    return render_template("static_page.html", page_title="Home", message="Welcome back to BabyBoost.")


@app.get("/stunting-prediction")
def stunting_prediction():
    return render_template(
        "static_page.html",
        page_title="Stunting Prediction",
        message="Open Growth Dashboard to update height and weight before reviewing prediction results.",
    )


@app.get("/healthy-recipes")
def healthy_recipes():
    return render_template(
        "static_page.html",
        page_title="Healthy Recipes",
        message="Meal inputs from the Growth Dashboard can be used to plan better daily nutrition.",
    )


@app.get("/parenting-guides")
def parenting_guides():
    return render_template(
        "static_page.html",
        page_title="Parenting Guides",
        message="Track growth consistently and review nutrition progress after each update.",
    )


@app.get("/forum")
def forum():
    return render_template("static_page.html", page_title="Forum", message="Share progress and questions with other parents.")


@app.get("/profile")
def profile():
    return render_template("static_page.html", page_title="Username", message="Your BabyBoost account is connected.")


@app.route("/growth-dashboard")
def select_child():
    return render_template("select_child.html", children=children.values())


@app.route("/growth-dashboard", methods=["POST"])
def confirm_child():
    child_id = request.form.get("child_id", "steve")
    return redirect(url_for("dashboard", child_id=child_id))


@app.post("/growth-dashboard/add-child")
def add_child():
    name = request.form.get("name", "").strip()
    age_months = request.form.get("age_months", type=int)
    height = request.form.get("height", type=float)
    weight = request.form.get("weight", type=float)
    if not name or age_months is None or height is None or weight is None:
        return redirect(url_for("select_child"))

    child = build_new_child(name, age_months, height, weight)
    children[child["id"]] = child
    save_children(children)
    return redirect(url_for("dashboard", child_id=child["id"]))


@app.route("/growth-dashboard/<child_id>")
def dashboard(child_id):
    period = request.args.get("range", "6_months")
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
        if height:
            child["height"] = height
        if weight:
            child["weight"] = weight
        if height and weight:
            child["bmi"] = round(weight / ((height / 100) ** 2), 1)
            child["history"].append(
                {
                    "month": datetime.now().strftime("%b %Y"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "height": round(height, 1),
                    "weight": round(weight, 1),
                }
            )
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
    return render_template("input_meal.html", child=child, food_names=food_names)


@app.get("/api/children")
def api_children():
    return jsonify([{"id": child["id"], "name": child["name"], "age": child["age"]} for child in children.values()])


@app.get("/api/children/<child_id>/growth")
def api_growth(child_id):
    child = current_child(child_id)
    if ensure_daily_nutrition(child):
        save_children(children)
    return jsonify(deepcopy(child))


@app.route("/api/children/<child_id>/growth", methods=["PUT", "PATCH"])
def api_update_growth(child_id):
    child = current_child(child_id)
    payload = request.get_json(silent=True) or {}
    height = payload.get("height")
    weight = payload.get("weight")
    if height is not None:
        child["height"] = float(height)
    if weight is not None:
        child["weight"] = float(weight)
    if height is not None and weight is not None:
        child["bmi"] = round(child["weight"] / ((child["height"] / 100) ** 2), 1)
        child["history"].append(
            {
                "month": datetime.now().strftime("%b %Y"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "height": round(child["height"], 1),
                "weight": round(child["weight"], 1),
            }
        )
    save_children(children)
    return jsonify(deepcopy(child))


@app.post("/api/children")
def api_add_child():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    age_months = payload.get("age_months")
    height = payload.get("height")
    weight = payload.get("weight")
    if not name or age_months is None or height is None or weight is None:
        return jsonify({"error": "name, age_months, height, and weight are required"}), 400
    child = build_new_child(name, int(age_months), float(height), float(weight))
    children[child["id"]] = child
    save_children(children)
    return jsonify(deepcopy(child)), 201


@app.post("/api/children/<child_id>/meal")
def api_add_meal(child_id):
    child = current_child(child_id)
    if ensure_daily_nutrition(child):
        save_children(children)
    payload = request.get_json(silent=True) or {}
    meal = str(payload.get("meal", "")).strip()
    if not meal:
        return jsonify({"error": "meal is required"}), 400
    child["meals"].append(meal)
    update_nutrition_after_meal(child, meal)
    save_children(children)
    return jsonify({"message": "meal saved", "meals": child["meals"]}), 201


if __name__ == "__main__":
    app.run(debug=True)
