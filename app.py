from flask import Flask # Call flask class
from flask import session, render_template, redirect, url_for, request
import key # another .py file
from helpers import lookup, login_required
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = key.SECRET_KEY

# Connect to SQL db - to be moved out of index
db_con = sqlite3.connect('users.db', check_same_thread=False)
db = db_con.cursor()

# Tell flask what URL should trigger functions
@app.route("/")
def index():
# @login_required
    dbTest = db.execute("SELECT * from users")
    print(db.fetchall())

    if session:
        print("Success")
        logout = "Log Out"
        return render_template('index.html', logout=logout)
    else:
        print(session)
        return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
# @login_required
def logout():
    # remove the username from the session if it's there
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Save name and password
    name = request.form.get("username")
    password = request.form.get("password")

     # for POST
    if (request.method == "POST"):

        # Retrieve the name of the user that is trying to register
        userCheck = db.execute("SELECT ? from users", [name])
        check = userCheck.fetchall()
        currentUser = check[0]

        if (not name):
            message = "You need to insert a username"
            return render_template("register.html", message=message)
        elif (not password):
            message = "The password is required!"
            return render_template("register.html", message=message)
        elif (request.form.get("password") != request.form.get("confirmation")):
            message = "Passwords do not match"
            return render_template("register.html", message=message)
        elif (name == currentUser[0]):
            message = "The user already exists."
            return render_template("register.html", message=message)

        # if all correct then create the account by adding the data into the table
        else:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (name, generate_password_hash(password,method='sha256')))
            return redirect("/")

    # for GET
    else:
        return render_template("register.html")

if __name__ == "__main__":
    app.run()


# Here you need to get the DB table, not sure how yet, to query from it for your search.
@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
    if request.method == "POST":
        title = request.form.get('movieTitle')
        movieArray = lookup(title)
        return render_template('search.html', movies=movieArray)
    elif request.method == "GET":        
        return render_template('search.html')


# for register

# if method is post
    # check if the 'name' || password exists in the SQL table
        # if does not exist
            # add the user to the database
        # else
            # show message that user exists and refresh the page
# else just generate regular register template