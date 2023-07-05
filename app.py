from flask import Flask # Call flask class
from flask import session, render_template, redirect, url_for, request
import key # another .py file
from helpers import lookup, login_required
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, '/static')
app.secret_key = key.SECRET_KEY

# Connect to SQL db - to be moved out of index
db_con = sqlite3.connect('users.db', check_same_thread=False)
db = db_con.cursor()

# Tell flask what URL should trigger functions
@app.route("/")
def index():

    if session:
        message = "Hello, " + session['username'] + "!"
        posterdb = db.execute("SELECT poster FROM rating WHERE user_id = ?", [session["user_id"]])
        posters = posterdb.fetchall()
        movies = []
        for row in posters:
            row = row[0]
            movies.append(row)
        print(movies)
        return render_template('index.html', welcomeUser=message, posters=movies)
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
    details = None
    message = ""

    for movie in checkMovie:
        if ("poster" in movie):
            if(movie['title'] == request.args.get("url_param")):
                poster = movie["poster"]
                details = movie["details"]
                movie_id = movie["id"]
                break

    entryExists = db.execute("SELECT rating FROM rating WHERE user_id = ? AND movie_id = ?", (session["user_id"], movie_id))
    fetchEntry = entryExists.fetchall()

    if request.method == "POST":
        if(fetchEntry):
            db.execute("UPDATE rating SET rating = ?, poster = ? WHERE user_id = ? AND movie_id = ?", (request.form.get("rates"), poster, session["user_id"], movie_id))
            db_con.commit()
            message = "New rate given: " + request.form.get("rates")
        else:
            db.execute("INSERT INTO rating (user_id, movie_id, rating, poster) VALUES (?, ?, ?, ?)", (session["user_id"], movie_id, request.form.get("rates"), poster))
            db_con.commit()
            message = "Rate given: " + request.form.get("rates")
    elif request.method == "GET":
        if(fetchEntry):
            message = "This has already been rated: " + str(fetchEntry[0][0])

    return render_template('movie.html', title=movieTitle, poster=poster, details=details, message=message)

@app.route("/people", methods=['GET'])
@login_required

def people():

    # fetch your movies
    currentUser = db.execute("SELECT movie_id, rating FROM rating WHERE user_id = ?", [session["user_id"]])
    userMovies = currentUser.fetchall()
    
    yourMovies = {}

    # Assign all your movies to a dict so it can later be compared against other user's movies
    for row in userMovies:
        yourMovies[row[0]] = row[1]
    print(yourMovies)

    # Create list of users where later points will be assigned
    faveUsers = {} # {user_id: totalPoints, user_id[1]: totalPoints}
    usersOnly = db.execute("SELECT username FROM users WHERE user_id IN (SELECT DISTINCT user_id FROM rating WHERE user_id != ?)", [session["user_id"]])
    userList = usersOnly.fetchall()

    for row in userList:
        faveUsers[row[0]] = 0
    print(faveUsers)

    # Fetch from rating all users except yourself and order the movies from highest ratest to lowest
    people = db.execute("SELECT u.username, r.user_id, r.movie_id, r.rating FROM users u JOIN rating r ON u.user_id = r.user_id WHERE r.user_id != ? ORDER BY rating DESC", [session["user_id"]])
    otherPeople = people.fetchall()

    for row in otherPeople:
        if row[2] in yourMovies:
            # Compare first only movies with 5 points on otherPeople db
            if row[3] == 5:
                # If the current user has the same movie with 5 points
                if row[3] == yourMovies[row[2]]:
                    # Grant the otherPeople user maximum amount of points (13)
                    faveUsers[row[0]] = faveUsers[row[0]] + row[3] + yourMovies[row[2]] + 3 # adding 3 additional points for max points
                elif row[3] == (yourMovies[row[2]] - 1):
                    # If you rated the movie but gave it less (4 points), otherPeople user will get points, but less (9 points)
                    faveUsers[row[0]] = faveUsers[row[0]] + row[3] + yourMovies[row[2]]
            elif row[3] == 4:
                # In case of otherPeople user's 4 points
                if row[3] == yourMovies[row[2]]:
                    # If same amount of points, the user gets 10 points
                    faveUsers[row[0]] = faveUsers[row[0]] + row[3] + yourMovies[row[2]] + 2 # adding 2 additional points for almost max
                elif row[3] == (yourMovies[row[2]] - 1) or row[3] == (yourMovies[row[2]] + 1):
                    # Otherwise if they gave 4 and you gave 3 or 5, the user will get 7 or 9 points (depending if you gave 3 or 5)
                    faveUsers[row[0]] = faveUsers[row[0]] + row[3] + yourMovies[row[2]]
            elif row[3] == 3 and row[3] == yourMovies[row[2]] or row[3] == (yourMovies[row[2]] + 1) or row[3] == (yourMovies[row[2]] - 1):
                # with 3 rating, it will either be 6 points in case of a match or 7 if you gave one more or 5 if you gave one less
                faveUsers[row[0]] = faveUsers[row[0]] + row[3] + yourMovies[row[2]]
            elif row[3] == 2 and row[3] == yourMovies[row[2]] or row[3] == (yourMovies[row[2]] + 1) or row[3] == (yourMovies[row[2]] - 1):
                faveUsers[row[0]] = faveUsers[row[0]] + row[3] + yourMovies[row[2]]
            elif row[3] == 1 and row[3] == yourMovies[row[2]] or row[3] == (yourMovies[row[2]] + 1):
                faveUsers[row[0]] = faveUsers[row[0]] + row[3] + yourMovies[row[2]]
            elif (row[3] - yourMovies[row[2]] > 2) or (row[3] - yourMovies[row[2]] < -2):
                # Minus 5 points for any movie with big discrepancy of points
                faveUsers[row[0]] = faveUsers[row[0]] - 5

        else:
            continue

            # check the algorithm, seems like it doesnt give the same amount of points to Mateusz vs Alejandro and Alejandro vs Mateusz,
            # for example.
            # In excel there are some points we gave to the movies to improve it.

    return render_template('people.html', people=faveUsers)