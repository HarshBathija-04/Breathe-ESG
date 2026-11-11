"""
Base parser: reads a CSV upload, maps headers, validates each row and stores it
as a RawRecord. Subclasses supply COLUMN_MAP, enrich_row() and validate_row().
"""
import csv
import io
from datetime import datetime

from apps.ingestion.models import RawRecord

DATE_FORMATS = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%d.%m.%Y', '%Y%m%d']


def parse_date(date_str):
    """Parse the date formats seen in SAP, utility and travel exports; None if unknown."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_cost(raw):
    """'$1,234.50' / '€99' -> float, or None."""
    try:
        return float(raw.replace(',', '').replace('$', '').replace('€', ''))
    except ValueError:
        return None


class BaseParserService:
    NAME = ''  # used in job log lines, e.g. "SAP parsing complete"
    PARSER_VERSION = ''
    COLUMN_MAP = {}
    LOG_VALIDATION_FAILURES = False

    def __init__(self, ingestion_job, source_system):
        self.job = ingestion_job
        self.source = source_system
        self.errors = []
        self.parsed_count = 0
        self.failed_count = 0

    def enrich_row(self, result):
        """Add derived/normalized fields to the row payload in place."""

    def validate_row(self, normalized):
        """Return a list of validation error messages (empty when valid)."""
        return []

    def is_skipped_row(self, raw_row):
        """Empty rows are skipped; subclasses can also skip footers."""
        return not any(v and v.strip() for v in raw_row.values())

    def parse_file(self, file_obj):
        """Parse the upload into RawRecords. Returns (parsed_count, failed_count, errors)."""
        rows = self.read_csv(file_obj)
        if not rows:
            self.log_error(0, 'No data rows found in file')
            return 0, 0, self.errors

        header_map = self._normalize_headers(rows[0].keys())
        self.job.add_log('INFO', f'Detected {len(rows)} rows with headers: {list(header_map.values())}')

        for idx, raw_row in enumerate(rows, start=1):
            try:
                if self.is_skipped_row(raw_row):
                    continue
                normalized = self._normalize_row(raw_row, header_map)
                validation_errors = self.validate_row(normalized)
                if validation_errors:
                    self.create_raw_record(normalized, idx, RawRecord.PARSE_FAILED, '; '.join(validation_errors))
                    self.failed_count += 1
                    if self.LOG_VALIDATION_FAILURES:
                        self.log_error(idx, 'Validation failed', {'errors': validation_errors})
                else:
                    self.create_raw_record(normalized, idx)
                    self.parsed_count += 1
            except Exception as e:
                self.failed_count += 1
                self.log_error(idx, f'Parse exception: {e}')

        self.job.add_log(
            'INFO', f'{self.NAME} parsing complete: {self.parsed_count} success, {self.failed_count} failed'
        )
        return self.parsed_count, self.failed_count, self.errors

    def _normalize_headers(self, raw_headers):
        """Map raw headers (possibly German) to normalized English keys."""
        normalized = {}
        for h in raw_headers:
            key = h.strip().lower().replace(' ', '_').replace('-', '_')
            normalized[h] = self.COLUMN_MAP.get(key, key)
        return normalized

    def _normalize_row(self, raw_row, header_map):
        result = {'_raw': dict(raw_row), '_parser_version': self.PARSER_VERSION}
        for raw_key, value in raw_row.items():
            result[header_map.get(raw_key, raw_key.lower().strip())] = value.strip() if value else ''
        self.enrich_row(result)
        return result

    def read_csv(self, file_obj, encoding='utf-8'):
        """Read the upload into a list of dict rows (BOM, latin-1 and delimiter tolerant)."""
        content = file_obj.read()
        if isinstance(content, bytes):
            try:
                text = content.decode(encoding)
            except UnicodeDecodeError:
                text = content.decode('latin-1')
        else:
            text = content
        text = text.removeprefix('﻿')

        # Sniff the delimiter: German SAP exports are semicolon-separated.
        first_line = text.split('\n', 1)[0]
        try:
            delimiter = csv.Sniffer().sniff(first_line, delimiters=',;\t|').delimiter
        except csv.Error:
            delimiter = ','

        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        # Drop overflow columns (DictReader keys them under None) so header handling stays simple.
        return [{k: v for k, v in row.items() if k is not None} for row in reader]

    def create_raw_record(self, payload, row_number, parse_status=RawRecord.PARSE_SUCCESS, parse_error=''):
        record = RawRecord(
            tenant=self.job.tenant,
            ingestion_job=self.job,
            source_system=self.source,
            original_payload=payload,
            row_number=row_number,
            parse_status=parse_status,
            parse_error=parse_error,
        )
        record.save()  # save() computes row_hash
        return record

    def log_error(self, row_number, message, details=None):
        error = {'row_number': row_number, 'message': message, 'details': details or {}}
        self.errors.append(error)
        self.job.add_log('ERROR', message, error)
