from unittest.mock import MagicMock, patch

from services.qa_service import (
    QAPair,
    generate_qa_pairs,
    save_qa_pairs_to_file,
)

# 姉妹リポジトリ grace_v2_local の同名テストにある `run_advanced_qa_generation` の検査は移植しない。
# 本リポジトリでは、存在しない `qa_generator_runner` を import する死にコードだったため
# 2026-09-12 に関数ごと削除している（`services/qa_service.py` の docstring）。


class TestQAService:

    @patch("services.qa_service.create_llm_client")
    def test_generate_qa_pairs(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Mock structured output
        mock_response = MagicMock()
        mock_qa = MagicMock()
        mock_qa.question = "Q1"
        mock_qa.answer = "A1"
        mock_qa.question_type = "factual"
        
        mock_response.qa_pairs = [mock_qa]
        mock_client.generate_structured.return_value = mock_response
        
        result = generate_qa_pairs("text", "dataset", "chunk1")
        
        assert len(result) == 1
        assert isinstance(result[0], QAPair)
        assert result[0].question == "Q1"
        assert result[0].source_chunk_id == "chunk1"
        # 本リポジトリの LLM（Anthropic）で生成する
        mock_create_client.assert_called_once_with(provider="anthropic")

    @patch("services.qa_service.pd.DataFrame.to_csv")
    @patch("services.qa_service.json.dump")
    @patch("builtins.open")
    @patch("services.qa_service.Path.mkdir")
    def test_save_qa_pairs_to_file(self, mock_mkdir, mock_open_file, mock_json_dump, mock_to_csv):
        qa_pairs = [
            QAPair(question="Q", answer="A", question_type="T", source_chunk_id="C", dataset_type="D")
        ]
        
        result = save_qa_pairs_to_file(qa_pairs, "dataset_type")
        
        assert "csv" in result
        assert "json" in result
        mock_to_csv.assert_called()
        mock_json_dump.assert_called()
