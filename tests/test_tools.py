from src.tools import search_documents


def test_search_documents_finds_relevant_file():
    result = search_documents("What guardrails does Bedrock provide?")
    assert "aws_bedrock_overview.txt" in result
    assert "Guardrails" in result


def test_search_documents_no_match():
    result = search_documents("zzqqxx wibbleflorp blorptastic nargle")
    assert result == "No matching documents found."
