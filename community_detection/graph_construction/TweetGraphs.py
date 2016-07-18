from database import DBManager
from igraph import *

# edge exists if tweet_graph has same hashtag
def construct_tweet_graph(graph, tweets):

    if graph is None:
        graph = Graph()

    hashtag_dict = {}
    for tweet in tweets:
        add_vertex(graph, tweet.id)
        hashtags = tweet.entities.get('hashtags')

        for hashtag in hashtags:
            tweet_id_list = hashtag_dict.get(hashtag["text"], [])

            for other_tweet_id in tweet_id_list:
                 graph.add_edge(str(tweet.id), str(other_tweet_id))

            tweet_id_list.append(tweet.id)
            hashtag_dict[hashtag["text"]] = tweet_id_list

    return graph


def add_vertex(graph, tweet_id):
    if not user_exists_in_graph(graph, tweet_id):
        new_vertex = graph.add_vertex(str(tweet_id))
        new_tweet = DBManager.get_or_add_tweet(tweet_id)
        if new_tweet is not None:
            graph.vs[graph.vcount()-1]["text"] = new_tweet.text
            # graph.vs[graph.vcount()-1]["sentiment"] = new_tweet.sentiment

    return graph

def user_exists_in_graph(graph, tweet_id):
    return graph.vcount() > 0 and graph.vs.select(name = str(tweet_id)).__len__() > 0