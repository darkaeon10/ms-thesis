import math
import random
from datetime import datetime

import nltk
import numpy
from sklearn import metrics

from data.parsing.csv_parser import CSVParser
from data.parsing.foldersio import FolderIO
from sentiment_analysis import SentimentClassifier
from sentiment_analysis.classifier.ClassifierIO import *
from sentiment_analysis.feature_extraction import FeatureExtractorBase
from sentiment_analysis.feature_extraction.UnigramExtractor import UnigramExtractor
from sentiment_analysis.preprocessing.PreProcessing import *


def train_or_load(pickle_file_name, trainer, training_set, force_train=False):
    classifier = None
    if not force_train:
        classifier = load_classifier_from_pickle(pickle_file_name)
    if not classifier:
        classifier = trainer.train(training_set)
        save_classifier_to_pickle(pickle_file_name, classifier)
    return classifier

def test_nltk():
    # read data
    LIMIT = 213

    row_generator = CSVParser.parse_file_into_csv_row_generator('sa_training_data/globe_dataset.csv')
    tweet_texts = [row[2] for row in row_generator][:LIMIT]

    row_generator = CSVParser.parse_file_into_csv_row_generator('sa_training_data/globe_dataset.csv')
    tweet_labels = [row[1] for row in row_generator][:LIMIT]

    # pre-process tweets
    TWEET_PREPROCESSORS = [SplitWordByWhitespace(), WordLengthFilter(3), WordToLowercase()]
    tweet_texts = preprocess_tweets(tweet_texts, TWEET_PREPROCESSORS)

    # construct labeled tweets to be run with the classifiers
    labeled_tweets = list(zip(tweet_texts, tweet_labels))


    # partition training/testing sets
    random.shuffle(labeled_tweets) # shuffling here to randomize train and test tweets
    num_train = math.floor(LIMIT * 0.6)
    train_tweets = labeled_tweets[:num_train]
    test_tweets = labeled_tweets[num_train:]

    print("# TRAIN: {}".format(train_tweets.__len__()))
    print("# TEST: {}".format(test_tweets.__len__()))

    # feature extraction
    FEATURE_EXTRACTOR = UnigramExtractor(train_tweets)
    FeatureExtractorBase.save_feature_extractor("unigram_feature_extractor.pickle", FEATURE_EXTRACTOR)
    training_set = nltk.classify.apply_features(FEATURE_EXTRACTOR.extract_features, train_tweets)

    # training
    TRAINER = nltk.NaiveBayesClassifier
    # TRAINER = SklearnClassifier(BernoulliNB())
    classifier = train_or_load("nb_classifier.pickle", TRAINER, training_set, True)
    print(classifier.show_most_informative_features(15))

    #classification
    test_set = nltk.classify.apply_features(FEATURE_EXTRACTOR.extract_features, test_tweets)
    print(nltk.classify.accuracy(classifier, test_set))


def write_metrics_file(actual_arr, predicted_arr, metrics_file_name):
    metrics_file = open(metrics_file_name, 'w')
    metrics_file.write('Total: {}\n'.format(actual_arr.__len__()))
    metrics_file.write('Accuracy: {}\n'.format(metrics.accuracy_score(actual_arr, predicted_arr)))
    metrics_file.write(metrics.classification_report(actual_arr, predicted_arr))
    metrics_file.write('\n')
    metrics_file.write(numpy.array_str(metrics.confusion_matrix(actual_arr, predicted_arr))) # ordering is alphabetical order of label names
    metrics_file.write('\n')
    metrics_file.close()

def test_senti_election_data():
    csv_files = FolderIO.get_files('D:/DLSU/Masters/MS Thesis/data-2016/senti_election_data/csv_files/test', False, '.csv')

    csv_rows = CSVParser.parse_files_into_csv_row_generator(csv_files, True)

    classifier = SentimentClassifier.LexiconClassifier()

    correct = 0
    total = 0

    actual_arr = []
    predicted_arr = []

    metrics_file_name = 'metrics-{}.txt'.format(datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))

    for csv_row in csv_rows:
        try:
            actual_class = csv_row[6]
            predicted_class = classifier.classify_sentiment(csv_row[1])

            if actual_class.lower() == predicted_class.lower():
                correct += 1
            total += 1

            print('{:.2f} = {}/{}'.format(correct/total, correct, total))

            actual_arr.append(actual_class.lower())
            predicted_arr.append(predicted_class.lower())

            if total % 500 == 0:
                write_metrics_file(actual_arr, predicted_arr, metrics_file_name)

        except Exception as e:
            print(e)
            pass


test_senti_election_data()

