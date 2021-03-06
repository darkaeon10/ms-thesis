import csv
import re

from tweepy import Status

from community_detection.graph_construction import TweetGraphs
from community_detection.graph_construction import MentionGraphs
from community_detection.weight_modification.EdgeWeightModifier import *
from sentiment_analysis.evaluation import TSVParser
from sentiment_analysis.preprocessing.PreProcessing import preprocess_strings
from twitter_data.SentiTweets import SentiTweetAdapter
from twitter_data.api import TweepyHelper
from twitter_data.database import DBManager
from twitter_data.database import DBUtils
from twitter_data.parsing.csv_parser import CSVParser
from twitter_data.parsing.folders import FolderIO
from twitter_data.parsing.json_parser import JSONParser


#########################################
### Base Graph Construction Functions ###
#########################################

##############################
### User Network Functions ###
##############################

def generate_network(file_name, tweet_objects, generation_func, verbose=False):
    GRAPH_PICKLE_FILE_NAME = file_name+".pickle"
    if verbose:
        print("Going to construct the graph")
    # construct graph based on user objects
    G = generation_func(None, tweet_objects, pickle_file_name=GRAPH_PICKLE_FILE_NAME, start_index=0, verbose=verbose)
    G.save(GRAPH_PICKLE_FILE_NAME)
    return G

def generate_user_network(file_name, tweet_objects, verbose=False):
    return generate_network(file_name, tweet_objects,TweetGraphs.construct_user_graph, verbose )

def generate_user_mention_network(file_name, tweet_objects, verbose=False):
    return generate_network(file_name, tweet_objects,TweetGraphs.construct_user_mention_graph, verbose )

def generate_user_mention_hashtag_sa_network(file_name, tweet_objects, classifier, THRESHOLD, hashtag_preprocessors=[], sa_preprocessors=[], verbose=False, load_mode=False):
    GRAPH_PICKLE_FILE_NAME = file_name+".pickle"
    if verbose:
        print("Going to construct the graph")
    # construct graph based on user objects
    G = MentionGraphs.construct_user_mention_hashtag_sa_graph(None, tweet_objects, classifier, GRAPH_PICKLE_FILE_NAME, THRESHOLD=THRESHOLD, hashtag_preprocessors=hashtag_preprocessors, sa_preprocessors=sa_preprocessors, verbose=verbose, load_mode=load_mode)
    G.save(GRAPH_PICKLE_FILE_NAME)
    return G

###############################
### Tweet Network Functions ###
###############################
def generate_tweet_hashtag_network(file_name, tweet_objects, sentiment_classifier, verbose=False):
    GRAPH_PICKLE_FILE_NAME = "{}.pickle".format(file_name)

    # Construct base graph
    print("Going to construct the graph")
    G = TweetGraphs.construct_tweet_hashtag_graph_with_sentiment(None, tweet_objects, GRAPH_PICKLE_FILE_NAME, sentiment_classifier)
    G.save(GRAPH_PICKLE_FILE_NAME)
    return G

##########################################
### Edge Weight Modification Functions ###
##########################################
def modify_network_weights(G, file_name, tweet_objects, edge_weight_modifiers, verbose=False):
    # Modify edge weights
    if verbose:
        print("Going to modify edge weights")
    G = modify_edge_weights(G, edge_weight_modifiers, {"tweets":tweet_objects, "with_context":True}, verbose)
    return G

################################################
### Community Detection & Analysis Functions ###
################################################
def determine_communities(G, out_file, verbose=False):
    # Community Detection
    if verbose:
        print("Going to determine communities")
    membership = G.community_infomap(edge_weights=G.es["weight"]).membership

    # Print metrics
    modularity = G.modularity(membership)
    print("Modularity: {}".format(modularity), file=out_file)

    return membership

def remove_communities_with_less_than_n(membership, n):
    return [m for m in membership if membership.count(m) >= n ]

def construct_graph_with_filtered_communities(g, membership, min_vertices_per_community):
    g = g.copy()
    valid_membership = remove_communities_with_less_than_n(membership, min_vertices_per_community)
    to_delete_ids = [v.index for v in g.vs if membership[v.index] not in valid_membership]
    g.delete_vertices(to_delete_ids)

    return (g, valid_membership)

def get_communities(membership):
    return sorted(list(set(membership)))

def get_vertex_ids_in_community(graph, membership, community_num):
    return [ index for index, x in enumerate(membership) if x == community_num]

def get_vertex_ids_in_each_community(graph, membership):
    communities = get_communities(membership)
    community_vertices = []
    for index, community in enumerate(communities):
        community_vertices.append(get_vertex_ids_in_community(graph, membership, index))
    return community_vertices

def get_vertex_ids_in_each_community_optimized(graph, membership, verbose=False):
    if len(membership) == 0:
        return []
    communities = range(max(membership)+1)
    community_vertices = [[] for x in communities]
    for vertex_id, community_num in enumerate(membership):
        community_vertices[community_num].append(vertex_id)
        if verbose:
            print("Grouping vertex IDs by community: {}/{}".format(vertex_id, len(membership)))
    return community_vertices

def get_user_ids_from_vertex_ids(graph, vertex_ids):
    return [vertex["name"] for vertex in graph.vs if vertex.index in vertex_ids]

def get_tweet_texts_belonging_to_user_ids(tweet_objects, user_ids_str):
    return [tweet.text for tweet in tweet_objects if tweet.user.id_str in user_ids_str]


#################################
### Dataset Loading Functions ###
#################################

def load_tweet_ids_from_vanzo_dataset():
    tsv_files = FolderIO.get_files("D:/DLSU/Masters/MS Thesis/data-2016/Context-Based_Tweets/conv_train", True, '.tsv')
    tsv_files += FolderIO.get_files("D:/DLSU/Masters/MS Thesis/data-2016/Context-Based_Tweets/conv_test", True, '.tsv')

    conversations = TSVParser.parse_files_into_conversation_generator(tsv_files)
    tweet_ids = [conversation[-1]["tweet_id"] for conversation in conversations]

    return tweet_ids


def load_tweet_ids_from_json_files(json_folder_path):
    tweet_files = FolderIO.get_files(json_folder_path, False, '.json')
    tweet_generator = JSONParser.parse_files_into_json_generator(tweet_files)
    # tweet_ids = [tweet["id"] for tweet in tweet_generator]
    tweet_ids = []
    for tweet in tweet_generator:
        try:
            tweet_ids.append(tweet["id"])
        except Exception as e:
            print(e)
            pass
    return list(set(tweet_ids))

def load_non_rt_tweet_ids_from_json_files(json_folder_path):
    tweet_files = FolderIO.get_files(json_folder_path, False, '.json')
    tweet_generator = JSONParser.parse_files_into_json_generator(tweet_files)

    tweet_ids = []
    for tweet in tweet_generator:
        try:
            if not re.match("rt\s@\S+:", tweet["text"].lower()):
                tweet_ids.append(tweet["id"])
        except Exception as e:
            print(e)
            pass
    return list(set(tweet_ids))

def load_tweet_objects_from_json_files(json_folder_path, limit=None):
    tweet_files = FolderIO.get_files(json_folder_path, False, '.json')
    tweet_generator = JSONParser.parse_files_into_json_generator(tweet_files)

    tweet_objects = []
    index = 0
    for tweet_json in tweet_generator:
        if limit:
            if index >= limit:
                break
            index += 1
        try:
            status = TweepyHelper.parse_from_json(tweet_json)
            #check if valid status; having limit in json means it was a rate limit response
            if "limit" not in status._json:
                #check if tweet_objects already contains status
                tweet_objects.append(status)
        except Exception as e:
            print(e)
            pass
    return tweet_objects

def load_tweet_objects_from_senti_csv_files(csv_folder_path, limit=None):

    USER_CSV_COL_INDEX = 1
    TEXT_CSV_COL_INDEX = 2

    csv_files = FolderIO.get_files(csv_folder_path, False, '.csv')
    csv_rows = CSVParser.parse_files_into_csv_row_generator(csv_files, True)

    if limit:
        senti_tweet_objects = [SentiTweetAdapter(csv_row[TEXT_CSV_COL_INDEX], csv_row[USER_CSV_COL_INDEX]) for index, csv_row in enumerate(csv_rows) if index < limit]
    else:
        senti_tweet_objects = [SentiTweetAdapter(csv_row[TEXT_CSV_COL_INDEX], csv_row[USER_CSV_COL_INDEX]) for csv_row in csv_rows]

    return senti_tweet_objects

def load_non_rt_tweet_objects_from_senti_csv_files(csv_folder_path, limit=None):

    USER_CSV_COL_INDEX = 1
    TEXT_CSV_COL_INDEX = 2

    csv_files = FolderIO.get_files(csv_folder_path, False, '.csv')
    csv_rows = CSVParser.parse_files_into_csv_row_generator(csv_files, True)

    if limit:
        senti_tweet_objects = [SentiTweetAdapter(csv_row[TEXT_CSV_COL_INDEX], csv_row[USER_CSV_COL_INDEX]) for index, csv_row in enumerate(csv_rows) if index < limit and not re.match("rt\s@\S+:", csv_row[TEXT_CSV_COL_INDEX].lower())]
    else:
        senti_tweet_objects = [SentiTweetAdapter(csv_row[TEXT_CSV_COL_INDEX], csv_row[USER_CSV_COL_INDEX]) for csv_row in csv_rows if not re.match("rt\s@\S+:", csv_row[TEXT_CSV_COL_INDEX].lower())]
    return senti_tweet_objects

#########################
### Utility Functions ###
#########################

def generate_stats_per_community(graph, vertex_ids_per_community, tweet_objects):
    stats = []
    dataset_users = [tweet.user.id_str for tweet in tweet_objects]
    for community_num, vertex_ids in enumerate(vertex_ids_per_community):

        user_ids = get_user_ids_from_vertex_ids(graph, vertex_ids)
        present_user_ids = [user_id for user_id in user_ids if user_id in dataset_users]

        tweet_texts = get_tweet_texts_belonging_to_user_ids(tweet_objects, user_ids)

        stats_string = "# of Users: {}\n# of Users who exist in the dataset: {}\n# of Tweets:{}"\
            .format(len(user_ids), len(present_user_ids), len(tweet_texts))

        stats.append(stats_string)
    return stats

def extract_vertices_in_communities(graph, membership):
    dict = {}
    num_communities = len(set(membership))

    for i in range(num_communities):
        dict[i] = set()

    community_info = list(zip(graph.vs(), membership))

    for vertex, community_number in community_info:
        dict[community_number].add(vertex)

    return dict

def generate_text_for_communities(graph, membership, tweet_objects, base_name, preprocessors=[], output_dir="texts"):
    texts_per_community = get_texts_per_community(
        graph,
        membership,
        tweet_objects,
        preprocessors = preprocessors
        )

    for index, texts in enumerate(texts_per_community):
        print("Raw texts: {}/{}".format(index, len(texts_per_community)))

        out_file = open("{}/{}-text-{}.csv".format(output_dir, base_name, index), "w", encoding="utf8", newline='')
        csv_writer = csv.writer(out_file, delimiter="\n", quoting=csv.QUOTE_ALL)
        csv_writer.writerow(texts)
        out_file.close()

    return texts_per_community


def get_texts_per_community(graph, membership, tweet_objects, preprocessors=[]):

    texts_per_community = []

    vertex_ids_per_community = get_vertex_ids_in_each_community_optimized(graph, membership)

    for community_num, vertex_ids in enumerate(vertex_ids_per_community):
        user_ids_str = get_user_ids_from_vertex_ids(graph, vertex_ids)
        tweet_texts = get_tweet_texts_belonging_to_user_ids(tweet_objects, user_ids_str)
        tweet_texts = preprocess_strings(tweet_texts, preprocessors)
        texts_per_community.append(tweet_texts)

    return texts_per_community

def combine_text_for_each_community(community_dict):
    text_dict = {}
    for community_number, vertex_set in community_dict.items():
        if len(vertex_set) > 5:
            text_dict[community_number] = combine_text_in_vertex_set(vertex_set)

    return text_dict

def combine_text_in_vertex_set(vertex_set):
    return " ".join([vertex["display_str"] for vertex in vertex_set])

def collect_following_followers(tweet_ids):
     # Retrieve tweets from the DB
    tweet_objects = DBUtils.retrieve_all_tweet_objects_from_db(tweet_ids, verbose=True)
    for index, tweet_obj in enumerate(tweet_objects):
        user_id_str = tweet_obj.user.id_str
        follower_ids = DBManager.get_or_add_followers_ids(user_id_str)
        following_ids = DBManager.get_or_add_following_ids(user_id_str)

        print("Collecting following/followers: Processed {}/{} tweets.".format(index+1, len(tweet_objects)))

def count_mentions(tweet_objects):
    count = 0
    for tweet_object in tweet_objects:
        count += len(tweet_object.entities.get('user_mentions'))
    return count

def load_function_words(path):
    with open(path, "r") as function_words_file:
        words = [word.strip() for word in function_words_file.readlines()]
    return words

