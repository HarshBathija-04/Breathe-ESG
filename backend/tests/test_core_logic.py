"""Unit tests for pure parsing/normalization helpers."""
import io

import pytest

from apps.emissions.insights import parse_briefing
from apps.ingestion.services.base_parser import BaseParserService
from apps.normalization.services.normalization_service import normalize_number_string


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('6709,84', '6709.84'),  # German decimal comma
        ('1.234,5', '1234.5'),
        ('1,234.5', '1234.5'),
        ('1,234', '1234'),  # English thousands separator
        ('35578.32', '35578.32'),
        (' -12 ', '-12'),
    ],
)
def test_normalize_number_string(raw, expected):
    assert normalize_number_string(raw) == expected


class _Parser(BaseParserService):
    def parse_file(self, file_obj):
        return self.read_csv(file_obj)


@pytest.mark.parametrize(('sep', 'qty'), [(',', '12.5'), (';', '12,5'), ('\t', '12,5')])
def test_read_csv_sniffs_delimiter(sep, qty):
    data = f'Werk{sep}Menge\nDE01{sep}{qty}\n'.encode()
    assert _Parser(None, None).parse_file(io.BytesIO(data)) == [{'Werk': 'DE01', 'Menge': qty}]


def test_parse_briefing_valid_json():
    out = parse_briefing('{"headline": "H", "summary": "S", "highlights": ["a"], "risks": [], "recommendations": ["r"]}')
    assert out == {'headline': 'H', 'summary': 'S', 'highlights': ['a'], 'risks': [], 'recommendations': ['r']}


def test_parse_briefing_extracts_embedded_json_and_falls_back():
    assert parse_briefing('Sure! {"headline": "X"} done')['headline'] == 'X'
    fallback = parse_briefing('plain prose answer')
    assert fallback['summary'] == 'plain prose answer' and fallback['highlights'] == []
