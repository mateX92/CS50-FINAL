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

    if session:
        message = "Hello, " + session['username'] + "!"
        return render_template('index.html', welcomeUser=message)
    else:
        return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    # Forget any user_id
    session.clear()

    if request.method == 'POST':

        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            message = "You need to insert a username"
            return render_template("login.html", message=message)
        elif not password:
            message = "You need to insert a password"
            return render_template("login.html", message=message)
        
        # get the db and query the user that tries to get in
        users = db.execute("SELECT * FROM users WHERE username = ?", [username])
        rows = users.fetchall()
        print(rows)
        print(len(rows))

        if len(rows) == 0:
            message = "Invalid username"
            return render_template("login.html", message=message)
        elif not check_password_hash(rows[0][2], request.form.get("password")): # 2 is for password as it is stored in 3rd column of users db
            message = "Invalid password!"
            return render_template("login.html", message=message)
        else:
            session['user_id'] = rows[0][0]
            session['username'] = rows[0][1]
            session.modified = True # inform Flask to save the changes to the session
            return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
@login_required

def logout():
    # remove the username from the session if it's there
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Save name and password
    name = request.form.get("username")
    password = request.form.get("password")

    # just to test
    test = db.execute("SELECT * from users")
    rows = test.fetchall()
    print(rows)

     # for POST
    if (request.method == "POST"):
        userExists = db.execute("SELECT * FROM users WHERE username = ?", [name])

        if (not name):
            message = "You need to insert a username"
            return render_template("register.html", message=message, users=rows)
        elif (not password):
            message = "The password is required!"
            return render_template("register.html", message=message, users=rows)
        elif (request.form.get("password") != request.form.get("confirmation")):
            message = "Passwords do not match"
            return render_template("register.html", message=message, users=rows)
        elif (userExists.fetchall()): # if able to retrieve data with that name from the db it means that such user already exists
            message = "The user already exists."
            return render_template("register.html", message=message, users=rows)

        # if all correct then create the account by adding the data into the table
        else:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (name, generate_password_hash(password,method='sha256')))
            db_con.commit() # to actually insert the data in the db

            return redirect(url_for('login'))


    # for GET
    else:
        return render_template("register.html", users=rows)

if __name__ == "__main__":
    app.run()


# Here you need to get the DB table, not sure how yet, to query from it for your search.
@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():

    movieList = []

    if request.method == "POST":
        title = request.form.get('movieTitle')
        movies = lookup(title)
        for movie in movies:
            movieList.append(movie['title'])
        return render_template('search.html', movies=movieList)
    elif request.method == "GET":
        return render_template('search.html')

@app.route("/movie", methods=['GET', 'POST'])
@login_required
def movie():
    movieTitle = request.args.get("url_param")
    checkMovie = lookup(movieTitle)

    poster = None

    for movie in checkMovie:
        if ("poster" in movie):
            if(movie['title'] == request.args.get("url_param")):
                poster = movie["poster"] # it seems it shows me posters for all the movies
                break
    return render_template('movie.html', title=movieTitle, poster=poster)
