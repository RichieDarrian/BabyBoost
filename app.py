from flask import Flask, render_template, request
import pickle
import numpy as np
import os
import webbrowser
import threading

app = Flask(__name__, template_folder='templates', static_folder='templates/static-assets', static_url_path='/static-assets')

# Load model
basedir = os.path.dirname(__file__)
model_path = os.path.join(basedir, 'model.pkl')

with open(model_path, 'rb') as f:
    model = pickle.load(f)

# ── Routes ──────────────────────────────────────────────
@app.route('/')
@app.route('/index.html')
def home():
    return render_template('index.html')

@app.route('/parenting-guides.html')
def parenting_guides():
    return render_template('parenting-guides.html')

@app.route('/parenting-article-example.html')
def parenting_article():
    return render_template('parenting-article-example.html')

@app.route('/stunting-prediction.html')
def stunting_prediction():
    return render_template('stunting-prediction.html')

@app.route('/prediction-results.html')
def hasil_prediksi():
    return render_template('stunting-results.html')

# ── Prediction ──────────────────────────────────────────

@app.route('/predict', methods=['POST'])
def predict():
    # --- Parse inputs ---
    gender_s    = str(request.form['gender'])
    gender      = 1 if gender_s == 'laki-laki' else 2

    age_years   = int(request.form['age_years'])
    age_months  = int(request.form['age_months'])
    total_months = (age_years * 12) + age_months

    height_cm   = float(request.form['height_cm'])
    weight_kg   = float(request.form['weight_kg'])

    # --- Run model ---
    features        = np.array([[gender, height_cm, total_months]])
    prediction      = model.predict(features)
    probability     = model.predict_proba(features)
    pred_confidence = round(float(np.max(probability)) * 100, 2)

    # --- Interpret prediction ---
    pred_label = prediction[0].lower().strip()

    if pred_label == 'severely stunted':
        result         = 'Severely Stunted'
        recommendation = (
            'Please seek medical attention immediately. Consult a pediatrician or nutritionist '
            'for a thorough nutritional assessment and a stunting intervention plan.'
        )
    elif pred_label == 'stunted':
        result         = 'Stunted'
        recommendation = (
            'We recommend scheduling a nutritional check-up with a pediatrician as soon as possible. '
            'Early intervention with a balanced diet can significantly improve growth outcomes.'
        )
    elif pred_label == 'tinggi':
        result         = 'Tall'
        recommendation = (
            "Your child's height is above average for their age, which is generally healthy. "
            'Continue providing balanced nutrition and keep up with regular growth check-ups.'
        )
    elif pred_label == 'normal':
        result         = 'Normal'
        recommendation = (
            'Keep up the great work! Continue providing a balanced, nutritious diet '
            "and attend regular health check-ups to support your child's continued healthy development."
        )
    else:
        result         = 'Unknown: ' + prediction[0]
        recommendation = 'An unexpected result was returned. Please double-check the input data and try again.'

    # --- BMI (only for children >= 24 months) ---
    if total_months >= 24:
        height_m = height_cm / 100
        bmi      = round(weight_kg / (height_m ** 2), 2)

        if bmi < 18.5:
            bmi_result     = 'Underweight'
            recommendation = (
                "Your child's BMI indicates underweight. Please consult a pediatrician "
                'to review their nutritional intake and growth plan.'
            )
        elif bmi < 25:
            bmi_result = 'Normal weight'
        elif bmi < 30:
            bmi_result = 'Overweight'
        else:
            bmi_result     = 'Obese'
            recommendation = (
                "Your child's BMI indicates obesity. Please consult a pediatrician "
                'to review their diet and develop a healthy weight management plan.'
            )
    else:
        bmi        = '-'
        bmi_result = 'Not available — child is under 24 months'

    return render_template(
        'stunting-results.html',
        age_years      = age_years,
        age_months     = age_months,
        total_months   = total_months,
        bmi            = bmi,
        bmi_result     = bmi_result,
        gender_s       = gender_s,
        height_cm      = height_cm,
        weight_kg      = weight_kg,
        result         = result,
        confidence     = pred_confidence,
        recommendation = recommendation,
    )

# ── Dev server ───────────────────────────────────────────

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        threading.Timer(1.25, open_browser).start()
    app.run(debug=True)