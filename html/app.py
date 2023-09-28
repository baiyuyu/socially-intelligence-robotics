from flask import Flask, render_template, request, redirect, url_for
import os
import sys
sys.path.insert(1, '/Users/byy/Desktop/vu/sir/TA-14.git/connectors/python')

from speech_recognition_framework import  run_nao

app = Flask(__name__, template_folder='.',  static_folder = r'C:\Users\daniy\Documents\vu\SIR\TA-14\html\images')

app.config['UPLOAD_PATH'] = os.path.abspath('uploads')
app.config['SAVE_PATH'] = os.path.abspath('mapped_files')
app.config['MASTER_PATH'] = os.path.abspath('master_files')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    file_path = os.path.join(app.config['UPLOAD_PATH'], uploaded_file.filename)
    if uploaded_file.filename != '':
        # uploaded_file.save(uploaded_file.filename)
        print(file_path)
        run_nao(file_path)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)