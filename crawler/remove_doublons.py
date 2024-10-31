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

    def check_new_article(self, article_text:str, verbose:bool = True):
        """
        Returns True if article_text is not similar to any other reference text
        """
        m = self._get_minhash(article_text)
        result = self.lsh.query(m)
        if result: 
            if verbose: 
                print('Found duplicate, discarding...')
                logging.info(f"Deduplication - found probable overlap with {result}")
            return False
        return True

    def _get_minhash(self, text, num_perm=128):
        # Tokenize text by splitting on whitespace or any preferred tokenizer
        tokens = [token.lower() for token in text.split() if len(token) > 1]
        
        # Creating shingles/ngrams
        n = 3
        shingles = set()
        for i in range(len(tokens) - n + 1):
            shingle = ' '.join(tokens[i:i + n])  # Form a shingle of k words
            shingles.add(shingle)

        # Create MinHash object with a number of permutations (hash functions)
        m = MinHash(num_perm=num_perm)
        
        # Update the MinHash object with each token
        for s in shingles:
            m.update(s.encode('utf8'))
        
        return m