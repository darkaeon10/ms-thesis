import math
import random
import pickle
from datetime import datetime
from os import path

from sentiment_analysis.evaluation import TSVParser
from twitter_data.database import DBManager

import nltk
import numpy
from sentiment_analysis.machine_learning.feature_extraction import FeatureExtractorBase
from sentiment_analysis.subjectivity.SubjectivityClassifier import MLSubjectivityClassifier
from sklearn import metrics

from twitter_data.parsing.csv_parser import CSVParser
from twitter_data.parsing.folders import FolderIO
from sentiment_analysis import SentimentClassifier
from sentiment_analysis.machine_learning.feature_extraction.UnigramExtractor import UnigramExtractor
from sentiment_analysis.preprocessing.PreProcessing import *

def save_classifier_to_pickle(pickle_file_name, classifier):
    pickle.dump(classifier, open( "{}.pickle".format(pickle_file_name), "wb"))

def load_classifier_from_pickle(pickle_file_name):
    return pickle.load(pickle_file_name)

def train_or_load(pickle_file_name, trainer, training_set, force_train=False):
    classifier = None
    if not force_train:
        classifier = load_classifier_from_pickle(pickle_file_name)
    if not classifier:
        classifier = trainer.train(training_set)
        save_classifier_to_pickle(pickle_file_name, classifier)
    return classifier


def read_data(source_dir, file_extension):
    dataset_files = FolderIO.get_files(source_dir, False, file_extension)
    conversation_generator = TSVParser.parse_files_into_conversation_generator(dataset_files)
    X = []
    Y = []
    for index, conversation in enumerate(conversation_generator):
        target_tweet = conversation[-1]
        tweet_id = target_tweet["tweet_id"]
        tweet_object = DBManager.get_or_add_tweet(tweet_id)
        if tweet_object and tweet_object.text:
            X.append(tweet_object.text)
            if target_tweet["class"] == 'neutral':
                Y.append('objective')
            else:
                Y.append('subjective')
            print("Constructing data lists. At index {}".format(index))

    return (X,Y)

def train_subj_classifier_with_nltk():
    # read data
    (X_train,Y_train) = read_data('D:/DLSU/Masters/MS Thesis/data-2016/Context-Based_Tweets/conv_train', '.tsv')
    (X_test, Y_test ) = read_data('D:/DLSU/Masters/MS Thesis/data-2016/Context-Based_Tweets/conv_test', '.tsv')

    # pre-process tweets
    TWEET_PREPROCESSORS = [SplitWordByWhitespace(), WordLengthFilter(3), RemovePunctuationFromWords(), WordToLowercase()]
    X_train = preprocess_strings(X_train, TWEET_PREPROCESSORS)
    X_test = preprocess_strings(X_test, TWEET_PREPROCESSORS)
    print("FINISHED PREPROCESSING")

    # construct labeled tweets to be run with the classifiers
    train_tweets = list(zip(X_train, Y_train))
    test_tweets = list(zip(X_test, Y_test))

    print("# TRAIN: {}".format(train_tweets.__len__()))
    print("# TEST: {}".format(test_tweets.__len__()))

    # feature extraction
    FEATURE_EXTRACTOR = UnigramExtractor(train_tweets)
    FeatureExtractorBase.save_feature_extractor("subj_unigram_feature_extractor_vanzo_conv_train.pickle", FEATURE_EXTRACTOR)
    training_set = nltk.classify.apply_features(FEATURE_EXTRACTOR.extract_features, train_tweets)

    # training
    TRAINER = nltk.NaiveBayesClassifier
    # TRAINER = SklearnClassifier(BernoulliNB())
    classifier = train_or_load("subj_nb_classifier_vanzo_conv_train", TRAINER, training_set, True)
    print(classifier.show_most_informative_features(15))

    #classification
    test_set = nltk.classify.apply_features(FEATURE_EXTRACTOR.extract_features, test_tweets)
    print(nltk.classify.accuracy(classifier, test_set))


print("HOY")
# train_subj_classifier_with_nltk()

def write_metrics_file(actual_arr, predicted_arr, metrics_file_name):
    metrics_file = open(metrics_file_name, 'w')
    metrics_file.write('Total: {}\n'.format(actual_arr.__len__()))
    metrics_file.write('Accuracy: {}\n'.format(metrics.accuracy_score(actual_arr, predicted_arr)))
    try:
        metrics_file.write(metrics.classification_report(actual_arr, predicted_arr))
    except Exception as e:
        print(e)
        pass
    metrics_file.write('\n')
    metrics_file.write(numpy.array_str(metrics.confusion_matrix(actual_arr, predicted_arr))) # ordering is alphabetical order of label names
    metrics_file.write('\n')
    metrics_file.close()

def test_on_vanzo_dataset(classifier):
    tsv_files = FolderIO.get_files('D:/DLSU/Masters/MS Thesis/data-2016/Context-Based_Tweets/conv_test', True, '.tsv')
    conversations = TSVParser.parse_files_into_conversation_generator(tsv_files)

    metrics_file_name = 'metrics-vanzo-eng-{}-{}.txt'.format(datetime.now().strftime('%Y-%m-%d-%H-%M-%S'), classifier.get_name())

    actual_arr = []
    predicted_arr = []

    for index, conversation in enumerate(conversations):
        target_tweet = conversation[-1]

        print("{} - {}".format(index, target_tweet["tweet_id"]))
        tweet_object = DBManager.get_or_add_tweet(target_tweet["tweet_id"])
        if tweet_object:
            predicted_class = classifier.classify_subjectivity(tweet_object.text)
            actual_class = 'objective' if target_tweet["class"] == 'neutral' else 'subjective'

            # print('{} vs {}'.format(predicted_class, actual_class))
            predicted_arr.append(predicted_class)
            actual_arr.append(actual_class)

        if index % 100 == 0 and index > 0:
            pickle.dump((actual_arr, predicted_arr), open( "{}.pickle".format(metrics_file_name), "wb" ) )
            write_metrics_file(actual_arr, predicted_arr, metrics_file_name)

    pickle.dump((actual_arr, predicted_arr), open( "{}.pickle".format(metrics_file_name), "wb" ) )
    write_metrics_file(actual_arr, predicted_arr, metrics_file_name)

# subjectivity_classifier = MLSubjectivityClassifier('C:/Users/user/PycharmProjects/ms-thesis/sentiment_analysis/subjectivity/subj_unigram_feature_extractor_vanzo_conv_train.pickle', 'C:/Users/user/PycharmProjects/ms-thesis/sentiment_analysis/subjectivity/subj_nb_classifier_vanzo_conv_train.pickle' )
# test_on_vanzo_dataset(subjectivity_classifier)
