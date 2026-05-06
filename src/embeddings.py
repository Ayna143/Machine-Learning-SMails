import os
import re
from typing import List, Optional, Sequence, Union

import numpy as np

DEFAULT_EMBEDDING_MODEL_ID = os.environ.get(
    'SM_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'
)

_MODEL_CACHE = None
_MODEL_ID_LOADED = None

def _get_sentence_transformer(model_id: Optional[str] = None):
    global _MODEL_CACHE, _MODEL_ID_LOADED
    mid = model_id or DEFAULT_EMBEDDING_MODEL_ID
    if _MODEL_CACHE is not None and _MODEL_ID_LOADED == mid:
        return _MODEL_CACHE
    from sentence_transformers import SentenceTransformer

    _MODEL_CACHE = SentenceTransformer(mid)
    _MODEL_ID_LOADED = mid
    return _MODEL_CACHE

def prepare_text_for_embedding(text: Union[str, None]) -> str:
    if not isinstance(text, str):
        return ''
    t = text.replace('\r\n', '\n').replace('\r', '\n')
    t = re.sub(r'\s+', ' ', t).strip()

    if len(t) > 12000:
        t = t[:12000]
    return t

def encode_texts(
    texts: Sequence[str],
    model_id: Optional[str] = None,
    batch_size: int = 64,
    show_progress: bool = False,
) -> np.ndarray:
    model = _get_sentence_transformer(model_id)
    prepared = [prepare_text_for_embedding(t) for t in texts]

    prepared = [p if p.strip() else ' ' for p in prepared]

    kwargs = {
        'batch_size': batch_size,
        'convert_to_numpy': True,
        'normalize_embeddings': False,
        'show_progress_bar': show_progress,
    }
    emb = model.encode(prepared, **kwargs)
    return np.asarray(emb, dtype=np.float32)
