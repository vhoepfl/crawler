from nltk.tokenize import word_tokenize
from nltk.util import ngrams
from time import time
import logging

class ROUGEFilter: 
    def __init__(self, threshold = 0.8) -> None:
        self.ref_articles = []
        self.ref_urls = []
        self.threshold = threshold

    def add_article(self, article_text:str, url:str):
        """
        Add a new article to the reference articles - if a future article is similar to this one, 
        it will be ignored as doublon. 
        """
        self.ref_articles.append(self._get_ngrams(article_text))
        self.ref_urls.append(url)

    def check_new_article(self, article_text:str):
        """
        Returns True if article_text is not similar to any other reference text
        """
        new_article_ngrams = self._get_ngrams(article_text)
        t0 = time()
        for i, ref_article in enumerate(self.ref_articles):
            score = self._calc_ngram_overlap(ref_article, new_article_ngrams)
            if score >= self.threshold:
                print('Found duplicate, discarding...')
                logging.info(f"Removing duplicates - found overlap of {score} with {self.ref_urls[i]}")
                return False
        return True

    def _get_ngrams(self, text):
        tokens = word_tokenize(text)
        tokens = [token.lower() for token in tokens if len(token) > 1] #same as unigrams
        res = set(ngrams(tokens, 3)) #Using trigrams
        return res

    def _calc_ngram_overlap(self, reference_ngrams, evaluated_ngrams): 
        """
        Returns a estimate for the ROUGE metric using the code from 
        https://github.com/nlpyang/PreSumm/blob/master/src/prepro/data_builder.py#L140
        More infos: 
        https://stackoverflow.com/questions/67543209/calculating-bleu-and-rouge-score-as-fast-as-possible
        """
        reference_count = len(reference_ngrams)
        evaluated_count = len(evaluated_ngrams)

        overlapping_ngrams = evaluated_ngrams.intersection(reference_ngrams)
        overlapping_count = len(overlapping_ngrams)

        if evaluated_count == 0:
            precision = 0.0
        else:
            precision = overlapping_count / evaluated_count

        if reference_count == 0:
            recall = 0.0
        else:
            recall = overlapping_count / reference_count

        f1_score = 2.0 * ((precision * recall) / (precision + recall + 1e-8))
        return f1_score