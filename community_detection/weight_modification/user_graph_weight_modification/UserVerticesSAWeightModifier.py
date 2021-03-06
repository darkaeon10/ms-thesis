from community_detection.weight_modification.EdgeWeightModifier import EdgeWeightModifierBase
from twitter_data.database import DBUtils

class UserVerticesSAWeightModifier(EdgeWeightModifierBase):
    def __init__(self, sentiment_classifier):
        self.classifier = sentiment_classifier

    def modify_edge_weights(self, graph, params, verbose):
        hashtag_sentiment_users_dict = {}
        tweets = params["tweets"]
        with_context = params["with_context"]

        if verbose:
            print("Constructing (hashtag, sentiment) -> user dictionary.")

        for index, tweet in enumerate(tweets):
            user_id_str = tweet.user.id_str
            if with_context:
                sentiment = self.classifier.classify_sentiment(tweet.text, {"conv_context":[x.text for x in DBUtils.retrieve_full_conversation(tweet.in_reply_to_status_id, [])]})
            else:
                sentiment = self.classifier.classify_sentiment(tweet.text, [])
            hashtags = [hashtag_dict["text"].lower() for hashtag_dict in tweet.entities.get('hashtags')]

            for hashtag in hashtags:
                hashtag_sentiment_set = self.get_or_add_hashtag_sentiment_set(hashtag_sentiment_users_dict, hashtag, sentiment )
                hashtag_sentiment_set.add(user_id_str)

            if verbose:
                print("UserVerticesSAWeightModifier: Processed {}/{} tweets".format(index+1, len(tweets)))

        if verbose:
            print("Going through edges.")

        total_weight_update = 0
        for index, edge in enumerate(graph.es):
            source_vertex_id = edge.source
            target_vertex_id = edge.target
            source_vertex_name = graph.vs[source_vertex_id]["name"]
            target_vertex_name = graph.vs[target_vertex_id]["name"]

            for key, user_set in hashtag_sentiment_users_dict.items():
                if source_vertex_name in user_set and target_vertex_name in user_set:
                    edge["weight"] += 1
                    total_weight_update += 1
                    # print("New edge weight of {} to {} is {}".format(source_vertex_name, target_vertex_name, edge["weight"]))

            if verbose:
                print("SAWeightModifier: Processed {}/{} edges".format(index+1, len(graph.es)))

        print("SA: Modified edges {} times.".format(total_weight_update))
        return graph

    def get_or_add_hashtag_sentiment_set(self, hashtag_sentiment_users_dict, hashtag, sentiment):
        hashtag_sentiment_set = hashtag_sentiment_users_dict.get((hashtag, sentiment), None)
        if not hashtag_sentiment_set:
            hashtag_sentiment_set = set()
            hashtag_sentiment_users_dict[(hashtag, sentiment)] = hashtag_sentiment_set

        return hashtag_sentiment_set