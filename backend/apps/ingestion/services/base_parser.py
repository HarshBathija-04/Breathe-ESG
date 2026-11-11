"""
Base parser service - defines the interface all parsers must implement.
Parsers convert uploaded files into RawRecords.
"""
import csv
import io
from abc import ABC, abstractmethod


class BaseParserService(ABC):
    """
    Abstract base for all source parsers.

    Each parser handles:
    1. File reading (CSV, JSON, etc.)
    2. Row-level extraction
    3. Hash computation for deduplication
    4. RawRecord creation
    """

    def __init__(self, ingestion_job, source_system):
        self.job = ingestion_job
        self.source = source_system
        self.errors = []
        self.parsed_count = 0
        self.failed_count = 0

    @abstractmethod
    def parse_file(self, file_obj):
        """
        Parse the uploaded file and create RawRecords.
        Must be implemented by each source-specific parser.

        Returns: (parsed_count, failed_count, errors)
        """
        pass

    def read_csv(self, file_obj, encoding='utf-8'):
        """Helper: read CSV file and yield dict rows."""
        content = file_obj.read()
        if isinstance(content, bytes):
            # Try to detect encoding
            try:
                text = content.decode(encoding)
            except UnicodeDecodeError:
                text = content.decode('latin-1')
        else:
            text = content

        # Handle BOM
        if text.startswith('\ufeff'):
            text = text[1:]

        # Sniff the delimiter: German SAP exports are semicolon-separated.
        first_line = text.split('\n', 1)[0]
        try:
            delimiter = csv.Sniffer().sniff(first_line, delimiters=',;\t|').delimiter
        except csv.Error:
            delimiter = ','

        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        # Drop overflow columns (DictReader keys them under None) so header handling stays simple.
        return [{k: v for k, v in row.items() if k is not None} for row in reader]

    def create_raw_record(self, payload, row_number, parse_status='SUCCESS', parse_error=''):
        """Helper: create a RawRecord from parsed payload."""
        from apps.ingestion.models import RawRecord

        record = RawRecord(
            tenant=self.job.tenant,
            ingestion_job=self.job,
            source_system=self.source,
            original_payload=payload,
            row_number=row_number,
            parse_status=parse_status,
            parse_error=parse_error,
        )
        record.compute_hash()
        record.save()
        return record

    def log_error(self, row_number, message, details=None):
        """Helper: log a parsing error."""
        error = {
            'row_number': row_number,
            'message': message,
            'details': details or {},
        }
        self.errors.append(error)
        self.job.add_log('ERROR', message, error)
