import re
import string

# Standard English stopwords list (self-contained, no external network downloads required)
STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are',
    'aren\'t', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both',
    'but', 'by', 'can', 'cannot', 'could', 'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t',
    'doing', 'don\'t', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadn\'t',
    'has', 'hasn\'t', 'have', 'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s', 'her', 'here',
    'here\'s', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll',
    'i\'m', 'i\'ve', 'if', 'in', 'into', 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s',
    'me', 'more', 'most', 'mustn\'t', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once',
    'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'shan\'t',
    'she', 'she\'d', 'she\'ll', 'she\'s', 'should', 'shouldn\'t', 'so', 'some', 'such', 'than', 'that',
    'that\'s', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'there\'s', 'these',
    'they', 'they\'d', 'they\'ll', 'they\'re', 'they\'ve', 'this', 'those', 'through', 'to', 'too',
    'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d', 'we\'ll', 'we\'re', 'we\'ve',
    'were', 'weren\'t', 'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s', 'which', 'while',
    'who', 'who\'s', 'whom', 'why', 'why\'s', 'with', 'won\'t', 'would', 'wouldn\'t', 'you', 'you\'d',
    'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours', 'yourself', 'yourselves'
}

# Contractions dictionary for standardization
CONTRACTIONS = {
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "can't": "cannot",
    "cannot": "cannot",
    "won't": "will not",
    "wouldn't": "would not",
    "shouldn't": "should not",
    "couldn't": "could not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "haven't": "have not",
    "hasn't": "has not",
    "hadn't": "had not"
}

# Negation words crucial for accurate sentiment and priority classification
NEGATION_WORDS = {'no', 'nor', 'not', 'never', 'none', 'cannot', 'without'}
EFFECTIVE_STOPWORDS = {w for w in STOPWORDS if w not in NEGATION_WORDS and w not in CONTRACTIONS}

def clean_text(text: str, remove_stopwords: bool = True) -> str:
    """
    Cleans and standardizes raw complaint text for NLP pipeline.
    Steps:
      1. Lowercase conversion
      2. Contraction normalization (e.g. don't -> do not)
      3. URL and email removal
      4. Punctuation and special symbol stripping
      5. Whitespace normalization
      6. Optional stopword removal (preserving key negation terms)
    """
    if not text or not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()

    # Expand contractions before stripping punctuation
    for contr, exp in CONTRACTIONS.items():
        text = text.replace(contr, exp)

    # Remove URLs and emails
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)

    # Remove special punctuation and digits
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)

    # Tokenize and normalize spaces
    tokens = text.split()

    if remove_stopwords:
        tokens = [token for token in tokens if token not in EFFECTIVE_STOPWORDS and len(token) > 1]
    else:
        tokens = [token for token in tokens if len(token) > 1]

    return " ".join(tokens)

