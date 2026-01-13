from pathlib import Path

from src.adapters.mfa_pressers import MFAPressersAdapter
from src.adapters.party_reports import PartyReportsAdapter


def test_mfa_qa_parsing(tmp_path: Path) -> None:
    html = Path("tests/fixtures/mfa_sample.html").read_text(encoding="utf-8")
    adapter = MFAPressersAdapter({"source_type": "mfa_presser", "source_org": "mfa"}, tmp_path)
    parsed = adapter.parse(html)
    segments = adapter.segment(parsed["text"])
    assert segments[0]["segment_type"] == "q_turn"
    assert segments[1]["segment_type"] == "a_turn"


def test_party_heading_detection(tmp_path: Path) -> None:
    html = Path("tests/fixtures/party_sample.html").read_text(encoding="utf-8")
    adapter = PartyReportsAdapter({"source_type": "party_report", "source_org": "cpc"}, tmp_path)
    parsed = adapter.parse(html)
    segments = adapter.segment(parsed["text"])
    assert any(seg["segment_type"] == "heading" for seg in segments)
