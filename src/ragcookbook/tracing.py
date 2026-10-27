"""Thin OpenTelemetry wrapper: real spans when the SDK is installed, no-ops otherwise.

Spans never record raw user text (privacy); only sizes, counts, and outcomes.
"""
from contextlib import contextmanager

try:
    from opentelemetry import trace

    _tracer = trace.get_tracer("ragcookbook")
except ImportError:  # offline/dev installs without the azure extra
    _tracer = None


class _NoSpan:
    def set_attribute(self, *_a, **_k):
        pass


@contextmanager
def span(name: str, **attributes):
    if _tracer is None:
        yield _NoSpan()
        return
    with _tracer.start_as_current_span(name) as s:
        for k, v in attributes.items():
            s.set_attribute(k, v)
        yield s
