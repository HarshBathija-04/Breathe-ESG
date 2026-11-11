"""
AI emissions briefing via Groq.

The backend aggregates the tenant's normalized activities into a compact,
numbers-only context (no raw payloads, no personal data) and asks the LLM to
write an executive briefing. Groq is only ever called from here, never from
the browser.
"""
import json
import logging

from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from apps.anomaly.models import AnomalyFlag
from apps.normalization.models import NormalizedActivity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior ESG and GHG Protocol analyst. You write short, specific executive "
    "briefings from aggregated emissions data. Use only the numbers provided; never invent "
    "figures. Quantities are kg CO2e unless stated; convert to tonnes (t CO2e) when clearer. "
    "Totals exclude flagged (unresolved anomaly) and rejected records; mention the excluded "
    "flagged volume as a data-quality risk when it is material. "
    "Respond with a JSON object with exactly these keys: "
    '"headline" (one sentence, max 20 words), '
    '"summary" (2-3 sentences), '
    '"highlights" (array of 3 short strings: notable facts with numbers), '
    '"risks" (array of 2-3 short strings: data-quality or compliance risks), '
    '"recommendations" (array of 3 short, actionable strings).'
)



class InsightsUnavailable(Exception):
    """AI is not configured or the provider failed; message is safe to show users."""

    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code


def _num(value):
    return round(float(value or 0), 1)


def build_context(tenant):
    """Aggregate the tenant's data into a small JSON-serialisable dict."""
    all_qs = NormalizedActivity.objects.filter(tenant=tenant)
    # Flagged records are suspect until resolved and rejected ones are out, so they stay out of totals.
    qs = all_qs.exclude(status__in=[NormalizedActivity.STATUS_FLAGGED, NormalizedActivity.STATUS_REJECTED])
    total = qs.aggregate(co2e=Sum('co2e'), n=Count('id'))
    flagged = all_qs.filter(status=NormalizedActivity.STATUS_FLAGGED).aggregate(co2e=Sum('co2e'), n=Count('id'))

    def grouped(field, limit=None):
        rows = qs.values(field).annotate(co2e=Sum('co2e'), n=Count('id')).order_by('-co2e')
        rows = rows[:limit] if limit else rows
        return [{field: r[field] or 'unknown', 'kg_co2e': _num(r['co2e']), 'records': r['n']} for r in rows]

    monthly = (
        qs.annotate(month=TruncMonth('period_start')).values('month')
        .annotate(co2e=Sum('co2e')).order_by('month')
    )
    anomalies = (
        AnomalyFlag.objects.filter(tenant=tenant, status=AnomalyFlag.STATUS_OPEN)
        .values('anomaly_type').annotate(n=Count('id')).order_by('-n')
    )
    statuses = all_qs.values('status').annotate(n=Count('id'))

    return {
        'total_kg_co2e': _num(total['co2e']),
        'record_count': total['n'],
        'excluded_flagged_records': {'records': flagged['n'], 'kg_co2e': _num(flagged['co2e'])},
        'by_scope': grouped('scope'),
        'by_category': grouped('category'),
        'top_sub_categories': grouped('sub_category', 6),
        'top_facilities': grouped('facility_code', 5),
        'monthly_kg_co2e': [
            {'month': r['month'].strftime('%Y-%m'), 'kg_co2e': _num(r['co2e'])} for r in monthly if r['month']
        ][-12:],
        'review_status_counts': {r['status']: r['n'] for r in statuses},
        'open_anomalies_by_type': {r['anomaly_type']: r['n'] for r in anomalies},
    }


def _as_list(value):
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()][:5]
    return [str(value)] if value else []


def parse_briefing(raw):
    """Coerce the model's JSON into the fixed response shape; fall back to plain text."""
    raw = (raw or '').strip()
    data = None
    for candidate in (raw, raw[raw.find('{'):raw.rfind('}') + 1]):
        try:
            data = json.loads(candidate)
            break
        except ValueError:
            continue
    if not isinstance(data, dict):
        return {'headline': 'Emissions briefing', 'summary': raw[:1500],
                'highlights': [], 'risks': [], 'recommendations': []}
    return {
        'headline': str(data.get('headline') or 'Emissions briefing')[:300],
        'summary': str(data.get('summary') or '')[:1500],
        'highlights': _as_list(data.get('highlights')),
        'risks': _as_list(data.get('risks')),
        'recommendations': _as_list(data.get('recommendations')),
    }


def generate_briefing(tenant):
    if not settings.GROQ_API_KEY:
        raise InsightsUnavailable('AI insights are not configured on this server.')

    context = build_context(tenant)
    if not context['record_count']:
        raise InsightsUnavailable('Upload some activity data first, then generate a briefing.', 400)

    import groq  # imported lazily so the app boots without the SDK configured

    client = groq.Groq(api_key=settings.GROQ_API_KEY, timeout=45, max_retries=1)
    request = {
        'model': settings.GROQ_TEXT_MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': 'Aggregated emissions data:\n' + json.dumps(context)},
        ],
        'temperature': 0.3,
        'max_completion_tokens': 2000,
    }
    try:
        try:
            completion = client.chat.completions.create(response_format={'type': 'json_object'}, **request)
        except groq.BadRequestError:
            # gpt-oss occasionally fails Groq's strict JSON validation; retry once in plain mode.
            completion = client.chat.completions.create(**request)
    except groq.RateLimitError:
        raise InsightsUnavailable('The AI service is busy right now. Please try again in a minute.', 429)
    except groq.APIError as exc:
        logger.warning('Groq request failed: %s status=%s', type(exc).__name__, getattr(exc, 'status_code', None))
        raise InsightsUnavailable('The AI service is temporarily unavailable. Please try again later.', 502)

    briefing = parse_briefing(completion.choices[0].message.content)
    briefing['model'] = settings.GROQ_TEXT_MODEL
    briefing['context'] = {k: context[k] for k in ('total_kg_co2e', 'record_count')}
    return briefing
