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
            message = "Invalid username!"
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
    firstPerson = sortedPeople[0][0]

    return render_template('people.html', people=sortedPeople, firstperson=firstPerson)

@app.route('/person')
@login_required

def person():

    username = request.args.get("url_param")
    posterdb = db.execute("SELECT poster, movie_title, description, rating FROM rating WHERE user_id IN (SELECT user_id FROM users WHERE username = ?) ORDER BY rating DESC", [username])
    posters = posterdb.fetchall()

    userMovies = db.execute("SELECT poster, movie_title, description, rating FROM rating WHERE user_id = ? ORDER BY rating DESC", [session["user_id"]])
    userMovies = userMovies.fetchall()
 
    # Create a dictionary with poster: title value pair in order to populate the poster and be able to click on it to get to the movie's page
    movies = {}
    commonMovies = {}

    # Assigning posters from userMovies to a variable to loop through them
    userMoviesPosters = [row[0] for row in userMovies]

    for row in posters:
        poster, title, description, rating = row
        # if the same poster already exists in current's user db we add it to commonMovies
        if poster in userMoviesPosters:
            print(f'poster in userMovies: {poster}')
            commonMovies[poster] = [title, description, rating]
        else:
        # otherwise its a movie the current user haven't rated
            movies[poster] = [title, description, rating]      

    # Fetch other information regarding the visited user
    gender = db.execute("SELECT gender FROM users WHERE user_id IN (SELECT user_id FROM users WHERE username = ?)", [username]) 
    gender = gender.fetchall()
    description = db.execute("SELECT description FROM users WHERE user_id IN (SELECT user_id FROM users WHERE username = ?)", [username])
    description = description.fetchall()
    genres = db.execute("SELECT genre FROM genres WHERE user_id IN (SELECT user_id FROM users WHERE username = ?)", [username])
    genres = genres.fetchall()

    return render_template('person.html', username=username,posters=movies,poster2=commonMovies,gender=gender[0][0], description=description[0][0], genres=genres)

@app.route('/message', methods=['POST', 'GET'])
@login_required

def message():

    # Get the recipient's username 
    recipient = request.args.get("url_param")

    if request.method == 'GET':
        messageCheck = db.execute("SELECT user_id, username, recipient_name, message, date FROM new_messages WHERE user_id = ? AND recipient_name = ? OR recipient_name = ? AND username = ? ORDER BY date DESC", (session["user_id"], recipient, session["username"], request.args.get("url_param")))
        messages = messageCheck.fetchall()
        return render_template('message.html', username=recipient, messages=messages)
    
    # If POST, insert the message to the db with current user's data
    if request.method == 'POST':
        timeCheck = db.execute("SELECT CURRENT_TIMESTAMP")
        time = timeCheck.fetchall()
        db.execute("INSERT INTO new_messages (user_id, username, recipient_name, message, date) VALUES (?, ?, ?, ?, ?)", (session["user_id"], session["username"], recipient, request.form.get("newMessage"), time[0][0]))
        db_con.commit()
        return redirect('message?url_param='+recipient)

@app.route('/profile', methods=['POST', 'GET'])
@login_required

def profile():

    if request.method == 'POST':
        if request.form.get('gender'):
            db.execute("UPDATE users SET gender = ? WHERE user_id = ?", (request.form.get('gender'), session["user_id"]))
            db_con.commit()
        if request.form.get('description'):
            db.execute("UPDATE users SET description = ? WHERE user_id = ?", (request.form.get('description'), session["user_id"]))
            db_con.commit()
        if request.form.get('genres'):
            # Select to see if the currect genre is already in db
            checkGenres = db.execute("SELECT genre FROM genres WHERE genre = ? AND user_id = ?", [request.form.get('genres'), session["user_id"]])
            checkGenresFetch = checkGenres.fetchall()

            # If it is and user clicks on it again, it should be deleted from db
            if checkGenresFetch:
                db.execute("DELETE FROM genres WHERE genre = ? AND user_id = ?", [request.form.get('genres'), session["user_id"]])
                db_con.commit()
            # Else add genre to favourite of that user
            else:
                db.execute("CREATE TABLE IF NOT EXISTS genres(user_id INTEGER, genre TEXT, FOREIGN KEY (user_id) REFERENCES users (user_id))")
                db.execute("INSERT INTO genres (user_id, genre) VALUES (?, ?)", (session["user_id"], request.form.get('genres')))
                db_con.commit()

    genderCheck = db.execute('SELECT gender FROM users WHERE user_id = ?', [session["user_id"]])
    gender = genderCheck.fetchall()
    gender = gender[0][0]

    descriptionCheck = db.execute('SELECT description FROM users WHERE user_id = ?', [session["user_id"]])
    description = descriptionCheck.fetchall()
    description = description[0][0]

    GenresCheck = db.execute('SELECT genre FROM genres WHERE user_id = ?', [session["user_id"]])
    genres = GenresCheck.fetchall()
    genre_list = [genre[0] for genre in genres]

    allGenres = ['Action', 'Comedy', 'Drama', 'Fantasy', 'Sci-Fi', 'Horror', 'Mystery', 'Romance', 'Thriller', 'Western', 'Sports', 'Adventure']

    return render_template('profile.html', gender=gender, description=description, genres=genre_list, allgenres=allGenres)