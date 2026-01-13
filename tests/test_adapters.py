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


def test_mfa_qa_parsing_with_reporter_prefix(tmp_path: Path) -> None:
    html = """
    <html>
    <head><title>记者会</title></head>
    <body>
    <p>记者问：请介绍情况。</p>
    <p>发言人答:有关情况如下。</p>
    </body>
    </html>
    """
    adapter = MFAPressersAdapter({"source_type": "mfa_presser", "source_org": "mfa"}, tmp_path)
    parsed = adapter.parse(html)
    segments = adapter.segment(parsed["text"])
    assert segments[0]["segment_type"] == "q_turn"
    assert segments[1]["segment_type"] == "a_turn"


def test_mfa_date_parsing_variants(tmp_path: Path) -> None:
    adapter = MFAPressersAdapter({"source_type": "mfa_presser", "source_org": "mfa"}, tmp_path)
    assert adapter._infer_date("2024年5月7日 例行记者会", "") == "2024-05-07"
    assert adapter._infer_date("2024-05-07 例行记者会", "") == "2024-05-07"
    assert adapter._infer_date("", "https://example.com/20240507/xyz.shtml") == "2024-05-07"


def test_mfa_listing_date_from_sibling(tmp_path: Path) -> None:
    html = """
    <html>
    <body>
      <div class="newsList">
        <div class="newsBd">
          <ul class="list1">
            <li><a href="202001/t123.shtml">例行记者会</a><span>2020-01-02</span></li>
          </ul>
        </div>
      </div>
    </body>
    </html>
    """
    adapter = MFAPressersAdapter({"source_type": "mfa_presser", "source_org": "mfa"}, tmp_path)
    docs = adapter._extract_docs(
        html,
        "https://www.mfa.gov.cn/web/wjdt_674879/fyrbt_674889/",
        [],
        set(),
    )
    assert len(docs) == 1
    assert docs[0]["date"] == "2020-01-02"


def test_party_heading_detection(tmp_path: Path) -> None:
    html = Path("tests/fixtures/party_sample.html").read_text(encoding="utf-8")
    adapter = PartyReportsAdapter({"source_type": "party_report", "source_org": "cpc"}, tmp_path)
    parsed = adapter.parse(html)
    segments = adapter.segment(parsed["text"])
    assert any(seg["segment_type"] == "heading" for seg in segments)
