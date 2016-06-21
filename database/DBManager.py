from pymongo import MongoClient
from tweets import TweepyHelper
from bson.json_util import dumps
from tweepy import *
import json

client = MongoClient('localhost', 27017)
db = client['twitter_db']
tweet_collection = db['tweet_collection']
user_collection = db['user_collection']
following_collection = db['following_collection']
followers_collection = db['followers_collection']

# Tweet-related

def get_or_add_tweet(tweet_id):
    return get_or_add(tweet_id, tweet_collection, TweepyHelper.retrieve_tweet, Status.parse)

def delete_tweet(tweet_id):
    tweet_collection.delete_one({"id":tweet_id})

# User-related

def get_or_add_user(user_id):
    return get_or_add(user_id, user_collection, TweepyHelper.retrieve_user, User.parse)

def delete_user(user_id):
    user_collection.delete_one({"id":user_id})

def get_or_add_following_ids(user_id):
    return get_or_add_list(user_id, following_collection, TweepyHelper.retrieve_following_ids, 'following_ids')

def get_or_add_followers_ids(user_id):
    return get_or_add_list(user_id, followers_collection, TweepyHelper.retrieve_followers_ids, 'followers_ids')

def delete_following_ids(user_id):
    following_collection.delete_one({"id":user_id})

def delete_followers_ids(user_id):
    followers_collection.delete_one({"id":user_id})


# Helper functions

def get_or_add_list(id, collection, retrieve_func, list_name):
    try:
        from_db = collection.find_one({'id':id})
        return from_db[list_name] if from_db else add_or_update_list_db(id, collection, retrieve_func, list_name)
    except:
        return None

def add_or_update_list_db(id, collection, retrieve_func, list_name):
    from_api = retrieve_func(id)
    if from_api:
        json = {"id":id, list_name:from_api}
        collection.update({"id":id}, json, True)
    return from_api

def get_or_add(id, collection, retrieve_func, obj_constructor):
    try:
        from_db = json.loads(dumps(collection.find_one({"id":id})))
        return obj_constructor(from_db) if from_db else add_or_update_db(id, collection, retrieve_func)
    except:
        return None

def add_or_update_db(id, collection, retrieve_func):
    from_api = retrieve_func(id)
    if from_api:
        collection.update({"id":id}, from_api._json, True)
    return from_api


