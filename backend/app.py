from flask import Flask, jsonify, request, render_template, redirect
from db import get_mysql_connection, get_mongo_collection
import mysql.connector

app = Flask(
    __name__,
    template_folder = "../frontend/template",
    static_folder = "../frontend/static"
)      

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods = ["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "admin1234":
            return redirect("/")
        else:
            return "Invalid username or password"
    return render_template("login.html")

@app.route("/register", methods = ["GET", "POST"])
def register():
    if request.method == 'POST': 
        return redirect('/login')
    return render_template('register.html')

if __name__ == '__main__':
    try:
        init_mysql_db()
    except Exception as e:
        print(f"Warning: DB init failed: {e}")

    app.run(host='0.0.0.0', port=5001, debug=True)