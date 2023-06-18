import os # To obtain API key
import requests
import urllib.parse
import urllib.request, json
from functools import wraps
from flask import g

def lookup(movie):
    """Look up movie title."""

    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://imdb-api.com/en/API/SearchMovie/{api_key}/{movie}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None
    
    # Parse response
    try:
        movies = []
        quote = response.json()
        movieResults = quote["results"]
        for movie in movieResults:
            movies.append(movie["title"])
        return movies
    except (KeyError, TypeError, ValueError):
        return None


def login_required(f):
    # f is the function for the route you are trying to protect and make accessible only to logged in user!
    @wraps(f) # preserves some metadata of the function to be protected
    def decorated_function(*args, **kwargs):
        if session["username"] is None: # "Username" comes from login function - maybe it should be placed on top
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs) # returns the protected route and function and includes any argument that is required for that function!
    return decorated_function

