import { describe, expect, it } from 'vitest';
import { formatCO2e, formatMonth, humanize, scopeLabel } from './format';
import { healthUrlFor, messageFromError } from './http';

describe('formatCO2e', () => {
  it('keeps small values in kg', () => expect(formatCO2e(512.34)).toBe('512.3 kg'));
  it('switches to tonnes and kilotonnes', () => {
    expect(formatCO2e(12_500)).toBe('12.5 t');
    expect(formatCO2e('3279000')).toBe('3.28 kt');
  });
  it('handles junk', () => expect(formatCO2e('abc')).toBe('-'));
});

describe('labels', () => {
  it('formats month keys', () => expect(formatMonth('2024-03')).toBe('Mar 24'));
  it('humanizes enums', () => expect(humanize('PENDING_REVIEW')).toBe('Pending review'));
  it('labels scopes', () => expect(scopeLabel('Scope2')).toBe('Scope 2'));
});

describe('http helpers', () => {
  it('derives the health URL from the API base', () => {
    expect(healthUrlFor('https://api.example.com/api')).toBe('https://api.example.com/health');
    expect(healthUrlFor('http://localhost:5110/api/')).toBe('http://localhost:5110/health');
  });
  it('prefers the API error message', () => {
    const err = {
      isAxiosError: true,
      response: { status: 400, data: { error: 'Invalid email or password.' } },
    };
    expect(messageFromError(err, 'fallback')).toBe('Invalid email or password.');
  });
  it('explains network failures', () => {
    expect(messageFromError({ isAxiosError: true, code: 'ERR_NETWORK' }, 'x')).toMatch(/reach the server/);
  });
  it('falls back', () => expect(messageFromError(new Error('boom'), 'fallback')).toBe('fallback'));
});
