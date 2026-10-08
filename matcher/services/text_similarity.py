"""Text similarity: TF-IDF + cosine similarity on item text.

Returns scores from 0.0 to 1.0. This is a PROJECT-DEFINED similarity of the
WORDS used in two reports. It is not a probability, and it does not
understand meaning (for example 'earbuds' vs 'headphones' scores 0).
"""
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Extra words that appear in almost every lost-and-found report
EXTRA_STOP_WORDS = {'lost', 'found', 'item', 'items', 'near', 'around', 'left', 'campus'}
STOP_WORDS = sorted(ENGLISH_STOP_WORDS | EXTRA_STOP_WORDS)


def item_text(item):
    """The text we compare: title + description.
    (Titles like 'Black boAt earbuds' contain the most important words.)"""
    return f'{item.title} {item.description}'


def text_similarities(query_text, candidate_texts, corpus_texts=None):
    """Compare ONE text with MANY candidate texts.

    corpus_texts: the collection of texts used to LEARN how rare each word is (IDF).
    If left out, the query and the candidates themselves are used.
    Returns a list of scores, one per candidate, in the same order."""
    candidate_texts = list(candidate_texts)
    if not candidate_texts or not (query_text or '').strip():
        return [0.0] * len(candidate_texts)

    training_texts = list(corpus_texts) if corpus_texts else [query_text] + candidate_texts
    vectorizer = TfidfVectorizer(stop_words=STOP_WORDS, sublinear_tf=True)
    try:
        vectorizer.fit(training_texts)  # learn the vocabulary and how rare each word is
        query_vector = vectorizer.transform([query_text])
        candidate_matrix = vectorizer.transform(candidate_texts)
    except ValueError:
        # Raised when every word was a stop word ("empty vocabulary")
        return [0.0] * len(candidate_texts)

    scores = cosine_similarity(query_vector, candidate_matrix)[0]
    return [round(max(0.0, min(1.0, float(s))), 4) for s in scores]


def text_similarity(text_a, text_b):
    """Compare two texts (a convenience wrapper)."""
    return text_similarities(text_a, [text_b])[0]


def shared_keywords(text_a, text_b):
    """Meaningful words that appear in BOTH texts (used to explain a match)."""
    analyzer = TfidfVectorizer(stop_words=STOP_WORDS).build_analyzer()
    return sorted(set(analyzer(text_a or '')) & set(analyzer(text_b or '')))