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

        posterdb = db.execute("SELECT poster, movie_title, description, rating FROM rating WHERE user_id = ?", [session["user_id"]])
        posters = posterdb.fetchall()
 
        # Create a dictionary with poster: title value pair in order to populate the poster and be able to click on it to get to the movie's page
        movies = {}
        for row in posters:
            poster, title, description, rating = row
            movies[poster] = [title, description, rating]

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



@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():

    movieList = {}

    if request.method == "POST":
        title = request.form.get('movieTitle')
        movies = lookup(title)
        for movie in movies:
            movieList[movie["details"]] = movie["title"]
        return render_template('search.html', movies=movieList)
    elif request.method == "GET":
        return render_template('search.html', movies=movieList)


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
            if(movie['details'] == request.args.get("url_param2")):
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
            db.execute("INSERT INTO rating (user_id, movie_id, rating, poster, movie_title, description) VALUES (?, ?, ?, ?, ?, ?)", (session["user_id"], movie_id, request.form.get("rates"), poster, movie["title"], details))
            db_con.commit()
            message = "Rate given: " + request.form.get("rates")
    elif request.method == "GET":
        if(fetchEntry):
            message = "This has already been rated: " + str(fetchEntry[0][0])

    return render_template('movie.html', title=movieTitle, poster=poster, details=details, message=message)

@app.route("/people", methods=['GET'])
@login_required

def people():

    # Fetch current user's movies and their rating
    currentUser = db.execute("SELECT movie_id, rating FROM rating WHERE user_id = ?", [session["user_id"]])
    userMovies = currentUser.fetchall()
    yourMovies = {}

    # Assign all your movies to a dict so it can later be compared against other user's movies
    for row in userMovies:
        yourMovies[row[0]] = row[1]

    # Create list of other users to which points will be assigned
    faveUsers = {} # {user_id: totalPoints, user_id[1]: totalPoints}
    userListTuple = db.execute("SELECT username FROM users WHERE user_id IN (SELECT DISTINCT user_id FROM rating WHERE user_id != ?)", [session["user_id"]])
    userList = userListTuple.fetchall()

    for row in userList:
        faveUsers[row[0]] = 0

    # Fetch from rating all users except current user and order the movies from highest ratest to lowest
    people = db.execute("SELECT u.username, r.user_id, r.movie_id, r.rating FROM users u JOIN rating r ON u.user_id = r.user_id WHERE r.user_id != ? ORDER BY rating DESC", [session["user_id"]])
    peopleList = people.fetchall()

    for row in peopleList:
        if row[2] in yourMovies:
            # We don't consider 2s and 1s for positive points as they are not very relevant
            if (row[3] >= 3 and yourMovies[row[2]] >=2) or (row[3] >= 2 and yourMovies[row[2]] >=3):
                # If the rating is the same, triplicate the rating and add to points
                if row[3] == yourMovies[row[2]]: 
                    faveUsers[row[0]] = faveUsers[row[0]] + (row[3] * 3)
                # If the rating is almost the same (difference of 1), sum the rating
                elif row[3] == (yourMovies[row[2]] + 1) or row[3] == (yourMovies[row[2]] - 1):
                    faveUsers[row[0]] = faveUsers[row[0]] + row[3] + yourMovies[row[2]]
                # If the rating difference is bigger than 2, provide negative points
                elif row[3] - yourMovies[row[2]] > 2 or row[3] - yourMovies[row[2]] < -2:
                    faveUsers[row[0]] = faveUsers[row[0]] - abs((row[3] - yourMovies[row[2]]) * 4)
            else:
                # The rating difference has to apply also for row[3] < 3 (e.g. when row[3] == 1 and yourMovies[row[2]] == 5)
                if row[3] - yourMovies[row[2]] > 2 or row[3] - yourMovies[row[2]] < -2:
                    faveUsers[row[0]] = faveUsers[row[0]] - abs((row[3] - yourMovies[row[2]]) * 4)
        else:
            continue

    faveUsersList = faveUsers.items()
    sortedPeople = sorted(faveUsersList, key=lambda x: x[1], reverse=True)

    return render_template('people.html', people=sortedPeople)

@app.route('/person')
@login_required

def person():

    username = request.args.get("url_param")
    posterdb = db.execute("SELECT poster, movie_title, description, rating FROM rating WHERE user_id IN (SELECT user_id FROM users WHERE username = ?) ORDER BY rating DESC", [username])
    posters = posterdb.fetchall()
 
    # Create a dictionary with poster: title value pair in order to populate the poster and be able to click on it to get to the movie's page
    movies = {}
    for row in posters:
        poster, title, description, rating = row
        movies[poster] = [title, description, rating]
    
    return render_template('person.html', username=username,posters=movies)

@app.route('/message', methods=['POST', 'GET'])
@login_required

def message():

    # Get the recipient's username 
    recipient = request.args.get("url_param")

    # If GET, show messages sent from current user to the selected user
    # TO FIX: the db is done wrong, I can see from Mateusz's profile what he sends to Alejandro, but not the other way around!
    # So basically I have a db with SENDER as username and RECEIVER as recipient_name
    # GET obtaines a db, but only the ones from SENDER (where user_id = ?)
    # so adding OR user_id = ? AND recipient_name = ? 
    # recipient in this case would be Mateusz, we are in his link. But Mateusz has never been a recipient and is still a sender
    # So how do I view messages where Mateusz is sender and Alejandro is recipient
    if request.method == 'GET':
        messageCheck = db.execute("SELECT user_id, username, recipient_name, message, date FROM new_messages WHERE user_id = ? AND recipient_name = ? OR recipient_name = ? AND username = ? ORDER BY date ASC", (session["user_id"], recipient, session["username"], request.args.get("url_param")))
        messages = messageCheck.fetchall()
        print(messages)
        return render_template('message.html', username=recipient, messages=messages)
    
    # If POST, insert the message to the db with current user's data
    if request.method == 'POST':
        timeCheck = db.execute("SELECT CURRENT_TIMESTAMP")
        time = timeCheck.fetchall()
        db.execute("INSERT INTO new_messages (user_id, username, recipient_name, message, date) VALUES (?, ?, ?, ?, ?)", (session["user_id"], session["username"], recipient, request.form.get("newMessage"), time[0][0]))
        db_con.commit()
        return redirect('message?url_param='+recipient)