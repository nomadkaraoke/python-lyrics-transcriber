import pytest
from unittest.mock import Mock, patch, MagicMock
import logging
import subprocess

# Mock the NLTK imports at module level before importing the handler
with patch('nltk.corpus.cmudict.dict', return_value={}):
    from lyrics_transcriber.correction.handlers.syllables_match import SyllablesMatchHandler

from lyrics_transcriber.types import GapSequence, Word, WordCorrection
from tests.test_helpers import create_test_gap_sequence


class TestSyllablesMatchHandler:
    """Test cases for SyllablesMatchHandler class."""

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_nlp(self):
        """Mock spacy nlp object."""
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_token1 = Mock()
        mock_token1._.syllables_count = 2
        mock_token2 = Mock()
        mock_token2._.syllables_count = 1
        mock_doc.__iter__.return_value = [mock_token1, mock_token2]
        mock_nlp.return_value = mock_doc
        mock_nlp.pipe_names = ["tagger"]
        mock_nlp.add_pipe = Mock()
        return mock_nlp

    @pytest.fixture
    def mock_pyphen_dic(self):
        """Mock pyphen dictionary."""
        mock_dic = Mock()
        mock_dic.inserted.return_value = "hel-lo"
        return mock_dic

    @pytest.fixture
    def mock_cmudict(self):
        """Mock NLTK CMU dictionary."""
        return {
            "hello": [["HH", "AH1", "L", "OW0"]],
            "world": [["W", "ER1", "L", "D"]],
            "test": [["T", "EH1", "S", "T"]],
        }

    @pytest.fixture
    def handler(self, mock_logger):
        """Handler instance for testing."""
        with patch('spacy.load') as mock_spacy_load:
            with patch('pyphen.Pyphen') as mock_pyphen:
                with patch('nltk.data.find'):
                    with patch('nltk.corpus.cmudict.dict', return_value={"hello": [["HH", "AH1", "L", "OW0"]]}):
                        with patch('syllables.estimate', return_value=2):
                            mock_nlp = Mock()
                            # Fix: make pipe_names a proper list
                            mock_nlp.pipe_names = ["tagger"]
                            mock_nlp.add_pipe = Mock()
                            mock_spacy_load.return_value = mock_nlp
                            mock_pyphen.return_value = Mock()
                            # Fix: create handler first, then set cmudict directly
                            handler = SyllablesMatchHandler(mock_logger)
                            handler.cmudict = {"hello": [["HH", "AH1", "L", "OW0"]]}
                            return handler

    @pytest.fixture
    def word_map(self):
        """Sample word map for testing."""
        return {
            "gap_word_1": Word(id="gap_word_1", text="hello", start_time=0.0, end_time=1.0),
            "gap_word_2": Word(id="gap_word_2", text="world", start_time=1.0, end_time=2.0),
            "ref_word_1": Word(id="ref_word_1", text="greetings", start_time=0.0, end_time=1.0),
            "ref_word_2": Word(id="ref_word_2", text="earth", start_time=1.0, end_time=2.0),
            "ref_word_3": Word(id="ref_word_3", text="hi", start_time=2.0, end_time=3.0),
        }

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_init_success(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test successful handler initialization."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_nlp.add_pipe = Mock()
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        assert handler.logger == mock_logger
        mock_spacy_load.assert_called_once_with("en_core_web_sm")
        mock_nlp.add_pipe.assert_called_once_with("syllables", after="tagger")

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    @patch('subprocess.check_call')
    def test_init_spacy_not_found_downloads_model(self, mock_subprocess, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test initialization when spacy model is not found but can be downloaded."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.side_effect = [OSError("Model not found"), mock_nlp]
        mock_pyphen.return_value = Mock()
        mock_subprocess.return_value = 0
        
        handler = SyllablesMatchHandler(mock_logger)
        
        assert mock_spacy_load.call_count == 2
        mock_subprocess.assert_called_once_with(["python", "-m", "spacy", "download", "en_core_web_sm"])

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    @patch('subprocess.check_call')
    def test_init_spacy_download_fails(self, mock_subprocess, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test initialization when spacy model download fails."""
        mock_spacy_load.side_effect = OSError("Model not found")
        mock_pyphen.return_value = Mock()
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "download")
        
        with pytest.raises(OSError, match="Language model 'en_core_web_sm' could not be downloaded"):
            SyllablesMatchHandler(mock_logger)

    @patch('nltk.corpus.cmudict.dict', side_effect=[LookupError("Resource not found"), {}])
    @patch('nltk.download')
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_init_cmudict_download(self, mock_spacy_load, mock_pyphen, mock_nltk_download, mock_cmudict, mock_logger):
        """Test initialization when NLTK cmudict needs to be downloaded."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        mock_nltk_download.assert_called_once_with("cmudict")

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_syllables_component_already_present(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test initialization when syllables component is already in pipeline."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger", "syllables"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        # add_pipe should not be called since component already exists
        mock_nlp.add_pipe.assert_not_called()

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_count_syllables_spacy(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test syllable counting using spacy."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        # Setup mock for spacy processing
        mock_token1 = Mock()
        mock_token1._.syllables_count = 2
        mock_token2 = Mock()
        mock_token2._.syllables_count = 1
        
        mock_doc = Mock()
        mock_doc.__iter__ = Mock(return_value=iter([mock_token1, mock_token2]))
        handler.nlp.return_value = mock_doc
        
        words = ["hello", "world"]
        result = handler._count_syllables_spacy(words)
        assert result == 3
        
        handler.nlp.assert_called_once_with("hello world")

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_count_syllables_spacy_none_values(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test syllable counting using spacy when syllables_count is None."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        # Setup mock for spacy processing with None values
        mock_token = Mock()
        mock_token._.syllables_count = None
        
        mock_doc = Mock()
        mock_doc.__iter__ = Mock(return_value=iter([mock_token]))
        handler.nlp.return_value = mock_doc
        
        words = ["hello"]
        result = handler._count_syllables_spacy(words)
        assert result == 1  # Should default to 1 when None

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_count_syllables_pyphen(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test syllable counting using pyphen."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_dic = Mock()
        mock_dic.inserted.side_effect = ["hel-lo", "world"]
        mock_pyphen.return_value = mock_dic
        
        handler = SyllablesMatchHandler(mock_logger)
        
        words = ["hello", "world"]
        result = handler._count_syllables_pyphen(words)
        assert result == 3  # hel-lo (2) + world (1)

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_count_syllables_pyphen_no_hyphenation(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test syllable counting using pyphen when no hyphenation is found."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_dic = Mock()
        mock_dic.inserted.return_value = ""
        mock_pyphen.return_value = mock_dic
        
        handler = SyllablesMatchHandler(mock_logger)
        
        words = ["hello"]
        result = handler._count_syllables_pyphen(words)
        assert result == 1  # Should default to 1

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_count_syllables_nltk(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test syllable counting using NLTK CMU dictionary."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        handler.cmudict = {
            "hello": [["HH", "AH1", "L", "OW0"]],  # 2 syllables (AH1, OW0)
            "world": [["W", "ER1", "L", "D"]],     # 1 syllable (ER1)
        }
        
        words = ["hello", "world"]
        result = handler._count_syllables_nltk(words)
        assert result == 3

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_count_syllables_nltk_word_not_found(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test syllable counting using NLTK when word is not in dictionary."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        handler.cmudict = {}
        
        words = ["unknown"]
        result = handler._count_syllables_nltk(words)
        assert result == 1  # Should default to 1

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    @patch('syllables.estimate')
    def test_count_syllables_lib(self, mock_estimate, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test syllable counting using syllables library."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        mock_estimate.side_effect = [2, 1]
        
        handler = SyllablesMatchHandler(mock_logger)
        
        words = ["hello", "world"]
        result = handler._count_syllables_lib(words)
        assert result == 3

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_count_syllables_integration(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test the main _count_syllables method."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        words = ["hello", "world"]
        
        with patch.object(handler, '_count_syllables_spacy', return_value=3):
            with patch.object(handler, '_count_syllables_pyphen', return_value=3):
                with patch.object(handler, '_count_syllables_nltk', return_value=3):
                    with patch.object(handler, '_count_syllables_lib', return_value=3):
                        result = handler._count_syllables(words)
                        
                        assert result == [3, 3, 3, 3]
                        handler.logger.debug.assert_called()

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_can_handle_no_reference_words(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger, word_map):
        """Test can_handle when no reference word IDs are available."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {"word_map": word_map})
        assert not can_handle
        assert data == {}

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_can_handle_no_word_map(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test can_handle when no word_map is provided."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {})
        assert not can_handle
        assert data == {}

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_can_handle_missing_word_id(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger, word_map):
        """Test can_handle when word ID is missing from word_map."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["missing_word_id"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        can_handle, data = handler.can_handle(gap, {"word_map": word_map})
        assert not can_handle
        assert data == {}

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_can_handle_matching_syllables(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger, word_map):
        """Test can_handle when syllable counts match."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        with patch.object(handler, '_count_syllables') as mock_count:
            mock_count.side_effect = [
                [3, 3, 3, 3],  # Gap syllables
                [3, 3, 3, 3],  # Reference syllables
            ]
            
            can_handle, data = handler.can_handle(gap, {"word_map": word_map})
            
            assert can_handle
            assert data["matching_source"] == "source1"

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_can_handle_no_matching_syllables(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger, word_map):
        """Test can_handle when syllable counts don't match."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        with patch.object(handler, '_count_syllables') as mock_count:
            mock_count.side_effect = [
                [2, 2, 2, 2],  # Gap syllables
                [3, 3, 3, 3],  # Reference syllables
            ]
            
            can_handle, data = handler.can_handle(gap, {"word_map": word_map})
            
            assert not can_handle
            assert data == {}

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_handle_without_data(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test handle method when data is not provided."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        with patch.object(handler, 'can_handle', return_value=(False, {})):
            corrections = handler.handle(gap)
            assert corrections == []

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_handle_multiple_gap_to_fewer_reference(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger, word_map):
        """Test handle when gap has more words than reference."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1", "gap_word_2"],  # 2 words
            reference_word_ids={"source1": ["ref_word_1"]},     # 1 word
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_1"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.create_word_combine_corrections') as mock_combine:
                mock_combine.return_value = [Mock(spec=WordCorrection)]
                
                corrections = handler.handle(gap, data)
                
                assert len(corrections) == 1
                mock_combine.assert_called_once()

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_handle_fewer_gap_to_multiple_reference(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger, word_map):
        """Test handle when gap has fewer words than reference."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],                    # 1 word
            reference_word_ids={"source1": ["ref_word_1", "ref_word_2"]},  # 2 words
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_1", "ref_word_2"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.create_word_split_corrections') as mock_split:
                mock_split.return_value = [Mock(spec=WordCorrection), Mock(spec=WordCorrection)]
                
                corrections = handler.handle(gap, data)
                
                assert len(corrections) == 2
                mock_split.assert_called_once()

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_handle_one_to_one_replacement(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger, word_map):
        """Test handle for one-to-one word replacement."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_1"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.create_word_replacement_correction') as mock_replacement:
                mock_replacement.return_value = Mock(spec=WordCorrection)
                
                corrections = handler.handle(gap, data)
                
                assert len(corrections) == 1
                mock_replacement.assert_called_once_with(
                    original_word="hello",
                    corrected_word="greetings",
                    original_position=0,
                    source="source1",
                    confidence=0.8,
                    reason="Source 'source1' had matching syllable count",
                    reference_positions={},
                    handler="SyllablesMatchHandler",
                    original_word_id="gap_word_1",
                    corrected_word_id="ref_word_1",
                )

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_handle_one_to_one_no_correction_needed(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger, word_map):
        """Test handle when words are identical (case insensitive)."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        word_map["gap_word_1"].text = "greetings"
        
        gap = GapSequence(
            transcribed_word_ids=["gap_word_1"],
            reference_word_ids={"source1": ["ref_word_1"]},
            transcription_position=0,
            preceding_anchor_id=None,
            following_anchor_id=None,
        )
        
        data = {
            "matching_source": "source1",
            "reference_word_ids": ["ref_word_1"],
            "word_map": word_map,
        }
        
        with patch('lyrics_transcriber.correction.handlers.word_operations.WordOperations.calculate_reference_positions', return_value={}):
            corrections = handler.handle(gap, data)
            
            assert corrections == []

    @patch('nltk.corpus.cmudict.dict', return_value={})
    @patch('pyphen.Pyphen')
    @patch('spacy.load')
    def test_inheritance_from_base_handler(self, mock_spacy_load, mock_pyphen, mock_cmudict, mock_logger):
        """Test that handler inherits from GapCorrectionHandler."""
        mock_nlp = Mock()
        mock_nlp.pipe_names = ["tagger"]
        mock_spacy_load.return_value = mock_nlp
        mock_pyphen.return_value = Mock()
        
        handler = SyllablesMatchHandler(mock_logger)
        
        from lyrics_transcriber.correction.handlers.base import GapCorrectionHandler
        assert isinstance(handler, GapCorrectionHandler) 