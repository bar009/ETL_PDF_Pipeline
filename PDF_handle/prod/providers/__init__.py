"""Provider integrations owned by the prod pipeline surface.

New code should call ``run_text`` / ``run_json`` and consume the uniform
``ProviderResult`` (see ``result.py``). The ``generate_*`` functions are the
legacy exception-raising shims kept for current step code.
"""

from PDF_handle.prod.providers.gemini import (
    MalformedProviderPayloadError,
    extract_json_payload,
    generate_content,
    generate_json_content,
    generate_text_content,
    run_json,
    run_text,
)
from PDF_handle.prod.providers.result import (
    ERROR_KINDS,
    ProviderError,
    ProviderResult,
    classify_error_kind,
)
