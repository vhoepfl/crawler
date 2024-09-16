from datasketch import MinHash, MinHashLSH
import logging

class MinHashFilter: 
    def __init__(self, threshold = 0.8) -> None:
        # Create an LSH index
        self.lsh = MinHashLSH(threshold=threshold, num_perm=128)

    def add_article(self, article_text:str, url:str):
        """
        Add a new article to the reference articles - if a future article is similar to this one, 
        it will be ignored as doublon. 
        """
        m = self._get_minhash(article_text)
        self.lsh.insert(url, m)

    def check_new_article(self, article_text:str):
        """
        Returns True if article_text is not similar to any other reference text
        """
        m = self._get_minhash(article_text)
        result = self.lsh.query(m)
        if result: 
            print('Found duplicate, discarding...')
            logging.info(f"Removing duplicates - found probable overlap of with {result}")
            return False
        return True

    def _get_minhash(self, text, num_perm=128):
        # Tokenize text by splitting on whitespace or any preferred tokenizer
        tokens = set([token.lower() for token in text.split() if len(token) > 1])
        
        # Create MinHash object with a number of permutations (hash functions)
        m = MinHash(num_perm=num_perm)
        
        # Update the MinHash object with each token
        for token in tokens:
            m.update(token.encode('utf8'))
        
        return m