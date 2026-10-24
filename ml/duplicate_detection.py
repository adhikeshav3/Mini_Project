from sklearn.metrics.pairwise import cosine_similarity
from ml.preprocessing import clean_text
from ml.predict import ModelManager
from config import Config

def find_duplicate_grievances(new_title: str, new_desc: str, existing_grievances: list, threshold: float = None) -> list:
    """
    Computes TF-IDF Cosine Similarity between a new grievance and existing grievances.
    Returns matches meeting or exceeding the similarity threshold.
    Does not automatically merge complaints. Flags them for review.
    """
    if not existing_grievances:
        return []
        
    if threshold is None:
        threshold = Config.SIMILARITY_THRESHOLD

    manager = ModelManager.get_instance()
    if not manager.is_loaded():
        manager.load_models()

    new_full = clean_text(f"{new_title}. {new_desc}")
    if not new_full:
        return []

    # Filter out empty grievances
    candidates = []
    cleaned_corpus = []
    
    for g in existing_grievances:
        c_text = clean_text(f"{g.title}. {g.description}")
        if c_text:
            candidates.append(g)
            cleaned_corpus.append(c_text)

    if not candidates:
        return []

    # Vectorize using the shared TF-IDF representation
    new_vec = manager.vectorizer.transform([new_full])
    corpus_vecs = manager.vectorizer.transform(cleaned_corpus)

    # Compute pairwise cosine similarities
    similarities = cosine_similarity(new_vec, corpus_vecs)[0]

    matches = []
    for idx, score in enumerate(similarities):
        score_val = float(score)
        if score_val >= threshold:
            g = candidates[idx]
            matches.append({
                'similar_grievance_id': g.grievance_id,
                'title': g.title,
                'category': g.predicted_category,
                'priority': g.predicted_priority,
                'status': g.status,
                'similarity_score': round(score_val, 3),
                'created_at': g.created_at.strftime('%Y-%m-%d %H:%M') if g.created_at else None
            })

    # Sort descending by similarity score
    matches.sort(key=lambda x: x['similarity_score'], reverse=True)
    return matches
