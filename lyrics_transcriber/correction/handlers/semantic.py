import torch
from transformers import AutoTokenizer, AutoModel
from typing import Dict, List, Optional, Set, Tuple

from lyrics_transcriber.types import GapSequence, Word, WordCorrection
from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler


class SemanticHandler(GapCorrectionHandler):
    """Handles corrections using transformer-based semantic similarity."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", similarity_threshold: float = 0.3):
        self.similarity_threshold = similarity_threshold
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def _get_embedding(self, text: str) -> torch.Tensor:
        """Get embedding for a piece of text."""
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1)

        return embedding

    def _get_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two pieces of text."""
        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)

        similarity = torch.nn.functional.cosine_similarity(emb1, emb2, dim=1)
        return similarity.item()

    def _find_best_match(self, word: str, reference_words: Dict[str, List[str]]) -> Tuple[Optional[str], float, Set[str]]:
        """Find the best matching reference word across all sources."""
        best_match = None
        best_similarity = 0.0
        matching_sources = set()

        # Get unique reference words
        all_ref_words = {w for words in reference_words.values() for w in words}

        for ref_word in all_ref_words:
            similarity = self._get_semantic_similarity(word, ref_word)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = ref_word
                matching_sources = {source for source, words in reference_words.items() if ref_word in words}

        return best_match, best_similarity, matching_sources

    def can_handle(self, gap: GapSequence, current_word_idx: int) -> bool:
        """Check if we can handle this gap."""
        return bool(gap.reference_words)

    def handle(self, gap: GapSequence, word: Word, current_word_idx: int, segment_idx: int) -> Optional[WordCorrection]:
        """Try to correct word based on semantic similarity."""
        if not word.text.strip():
            return None

        best_match, similarity, matching_sources = self._find_best_match(word.text, gap.reference_words)

        if best_match and similarity >= self.similarity_threshold and best_match.lower() != word.text.lower():
            return WordCorrection(
                original_word=word.text,
                corrected_word=best_match,
                segment_index=segment_idx,
                word_index=current_word_idx,
                confidence=similarity,
                source=", ".join(matching_sources),
                reason=f"Semantic similarity ({similarity:.2f})",
                alternatives={},
            )

        return None
