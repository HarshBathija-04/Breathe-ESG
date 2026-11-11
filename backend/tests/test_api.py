"""API smoke tests against the seeded demo tenant."""
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.normalization.models import NormalizedActivity

pytestmark = pytest.mark.django_db

SAMPLES = Path(settings.BASE_DIR) / 'sample_data'


def test_health_ok(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json() == {'status': 'ok', 'db': 'ok'}


def test_health_reports_db_down(client):
    with mock.patch('esg_platform.urls.connection') as conn:
        conn.cursor.side_effect = Exception('db down')
        res = client.get('/health')
    assert res.status_code == 503
    assert res.json() == {'status': 'error', 'db': 'error'}


def test_login_rejects_bad_password_with_json_error(client):
    res = client.post('/api/auth/login/', {'email': 'admin@democorp.com', 'password': 'nope'}, format='json')
    assert res.status_code == 400
    assert res.json()['error'] == 'Invalid email or password.'


def test_login_validates_input(client):
    res = client.post('/api/auth/login/', {'email': 'not-an-email'}, format='json')
    assert res.status_code == 400
    assert res.json()['code'] == 'validation_error'


def test_register_endpoint_removed(client):
    res = client.post('/api/auth/register/', {'email': 'x@y.z', 'password': 'p', 'role': 'admin'}, format='json')
    assert res.status_code == 404


def test_protected_endpoint_requires_token(client):
    res = client.get('/api/dashboard/stats/')
    assert res.status_code == 401
    assert res.json()['code'] == 'not_authenticated'


def test_me(analyst):
    res = analyst.get('/api/auth/me/')
    assert res.status_code == 200
    assert res.json()['role'] == 'analyst'


def test_invalid_uuid_is_404_not_500(analyst):
    res = analyst.get('/api/activities/not-a-uuid/')
    assert res.status_code == 404
    assert res.json()['code'] == 'not_found'


def test_dashboard_excludes_flagged_and_rejected(analyst):
    data = analyst.get('/api/dashboard/stats/').json()
    acts = data['activities']
    assert acts['total'] > 100 and acts['locked'] > 0 and acts['flagged'] > 0
    reportable = sum(row['count'] for row in data['emissions_by_scope'])
    assert reportable == acts['total'] - acts['flagged'] - acts['rejected']
    assert data['flagged_co2e'] > 0
    assert data['emissions_by_month']


def test_activities_ordering_is_whitelisted(analyst):
    res = analyst.get('/api/dashboard/activities/?ordering=password')
    assert res.status_code == 200


def test_seed_parses_german_decimal_commas():
    # sap_fuel_german.csv: "6709,84" tonnes of diesel -> 6,709,840 kg
    assert NormalizedActivity.objects.filter(activity_value=Decimal('6709840')).exists()


def test_seed_flags_impossible_trip():
    trip = NormalizedActivity.objects.get(category='travel', activity_value=Decimal('225000000'))
    assert trip.status == NormalizedActivity.STATUS_FLAGGED


def test_upload_sap_csv_runs_pipeline(analyst):
    upload = SimpleUploadedFile('sap_fuel.csv', (SAMPLES / 'sap_fuel.csv').read_bytes(), content_type='text/csv')
    res = analyst.post('/api/ingest/sap/', {'file': upload}, format='multipart')
    assert res.status_code == 200, res.content
    job = res.json()
    assert job['status'] in ('COMPLETED', 'PARTIAL')
    assert job['normalized_rows'] > 0


def test_upload_rejects_non_csv(analyst):
    upload = SimpleUploadedFile('evil.exe', b'MZ', content_type='application/octet-stream')
    res = analyst.post('/api/ingest/sap/', {'file': upload}, format='multipart')
    assert res.status_code == 400


def _pending_id():
    return NormalizedActivity.objects.filter(status=NormalizedActivity.STATUS_PENDING_REVIEW).values_list(
        'id', flat=True).first()


def test_analyst_cannot_approve(analyst):
    res = analyst.post(f'/api/review/{_pending_id()}/action/', {'decision': 'APPROVE'}, format='json')
    assert res.status_code == 403


def test_reviewer_approves(reviewer):
    activity_id = _pending_id()
    res = reviewer.post(f'/api/review/{activity_id}/action/', {'decision': 'APPROVE', 'reason': 'ok'}, format='json')
    assert res.status_code == 200
    assert NormalizedActivity.objects.get(id=activity_id).status == NormalizedActivity.STATUS_APPROVED


def test_bulk_approve_validates_ids(reviewer):
    res = reviewer.post('/api/review/bulk-approve/', {'activity_ids': ['x']}, format='json')
    assert res.status_code == 400


def test_ai_insights_not_configured(analyst, settings):
    settings.GROQ_API_KEY = ''
    res = analyst.post('/api/dashboard/insights/')
    assert res.status_code == 503
    assert res.json()['code'] == 'ai_unavailable'


def _fake_completion(content):
    message = mock.Mock(content=content)
    return mock.Mock(choices=[mock.Mock(message=message)])


def test_ai_insights_with_mocked_groq(analyst, settings):
    settings.GROQ_API_KEY = 'test-key'
    payload = '{"headline": "Scope 1 dominates", "summary": "S", "highlights": ["h"], "risks": ["r"], "recommendations": ["x"]}'
    with mock.patch('groq.Groq') as groq_cls:
        groq_cls.return_value.chat.completions.create.return_value = _fake_completion(payload)
        res = analyst.post('/api/dashboard/insights/')
    assert res.status_code == 200
    body = res.json()
    assert body['headline'] == 'Scope 1 dominates'
    assert body['context']['record_count'] > 0
    sent = groq_cls.return_value.chat.completions.create.call_args.kwargs
    assert sent['model'] == 'openai/gpt-oss-120b'


def test_ai_insights_rate_limited_upstream(analyst, settings):
    import groq

    settings.GROQ_API_KEY = 'test-key'
    err = groq.RateLimitError('slow down', response=mock.Mock(status_code=429, headers={}), body=None)
    with mock.patch('groq.Groq') as groq_cls:
        groq_cls.return_value.chat.completions.create.side_effect = err
        res = analyst.post('/api/dashboard/insights/')
    assert res.status_code == 429


def test_analyst_cannot_resolve_anomaly(analyst):
    from apps.anomaly.models import AnomalyFlag

    flag = AnomalyFlag.objects.filter(status=AnomalyFlag.STATUS_OPEN).first()
    res = analyst.post(f'/api/anomalies/{flag.id}/resolve/', {'status': 'RESOLVED'}, format='json')
    assert res.status_code == 403
