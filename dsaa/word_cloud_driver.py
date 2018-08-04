import os

import numpy
from PIL import Image

import settings
from analysis.word_cloud import word_cloud_generator
from dsaa import text_loader, utils
### Some Constants ###
from sentiment_analysis.preprocessing import PreProcessing

OUTPUT_DIR = '{}/dsaa_results/word_clouds/'.format(settings.PROJECT_ROOT)
brexit_coloring = numpy.array(Image.open("{}/uk_flag.png".format(settings.PROJECT_ROOT)))

preprocessors = [PreProcessing.SplitWordByWhitespace(),
                 PreProcessing.WordToLowercase(),
                 PreProcessing.ReplaceURL(replacement_token="<url>"),
                 PreProcessing.RemoveTerm("<url>"),
                 PreProcessing.RemoveExactTerms(["#brexit"]),
                 PreProcessing.RemovePunctuationFromWords(),
                 PreProcessing.RemoveRT(),
                 PreProcessing.RemoveLetterRepetitions(),
                 PreProcessing.WordLengthFilter(3),
                 PreProcessing.RemoveHashtagSymbol(),
                 PreProcessing.ConcatWordArray()]

if __name__ == "__main__":

    utils.create_path_if_not_exists(OUTPUT_DIR)

    # Read CSV for each community

    for config in text_loader.CONFIGS:
        print("### {} ###".format(config))
        dir = os.path.join(text_loader.TEXTS_ROOT_DIR, config)

        community_docs = text_loader.load_community_docs(dir)
        community_docs = [PreProcessing.preprocess_strings(x, preprocessors)
                          for x in community_docs]

        scheme_texts = []
        for x in community_docs:
            scheme_texts.extend(x)

        output_file = "{}/{}.png".format(OUTPUT_DIR, config)

        word_cloud_generator.generate_word_cloud(scheme_texts,
                                                 output_file,
                                                 mask=None,
                                                 colors=None)

        for community_num, docs in enumerate(community_docs):
            print("Community {}".format(community_num))

            dir = "{}/{}".format(OUTPUT_DIR, config)
            utils.create_path_if_not_exists(dir)

            output_file = "{}/{}-community-{}.png".format(dir, config, community_num)

            word_cloud_generator.generate_word_cloud(docs,
                                                     output_file,
                                                     mask=None,
                                                     colors=None)