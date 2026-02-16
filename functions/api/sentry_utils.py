"""
Sentry utilities for distributed tracing in Cloud Functions
Provides decorator to continue traces from frontend requests
"""

import functools
import logging
from typing import Callable, Any

import sentry_sdk
from firebase_functions.https_fn import Request

logger = logging.getLogger(__name__)


def with_sentry_trace(func: Callable) -> Callable:
    """
    Decorator to wrap Cloud Functions with Sentry distributed tracing.
    
    Extracts sentry-trace and baggage headers from incoming requests to continue
    the trace from the frontend. Creates a transaction that is a child of the
    frontend trace.
    
    Usage:
        @on_request(cors=CorsOptions(...))
        @with_sentry_trace
        def my_endpoint(req: Request):
            ...
    """
    @functools.wraps(func)
    def wrapper(req: Request, *args: Any, **kwargs: Any) -> Any:
        # Extract trace headers from incoming request
        sentry_trace_header = req.headers.get("sentry-trace")
        baggage_header = req.headers.get("baggage")
        
        # Get endpoint name from function name
        endpoint_name = func.__name__
        
        # Extract userId from query params or body for tagging
        user_id = None
        try:
            user_id = req.args.get("userId")
            if not user_id:
                # Try to get from JSON body
                body = req.get_json(silent=True) or {}
                user_id = body.get("userId")
        except Exception:
            pass
        
        # Parse sentry-trace header to continue trace from frontend
        trace_id = None
        parent_span_id = None
        sampled = None
        
        if sentry_trace_header:
            # Parse sentry-trace header format: trace_id-parent_span_id-sampled
            # Example: "566e3688ebcd4638ad8b8f0cdee66e5b-566e3688ebcd4638-1"
            parts = sentry_trace_header.split("-")
            if len(parts) >= 2:
                trace_id = parts[0]
                parent_span_id = parts[1]
                if len(parts) >= 3:
                    sampled = parts[2] == "1"
                logger.debug(
                    "Continuing trace: trace_id=%s, parent_span_id=%s, sampled=%s",
                    trace_id,
                    parent_span_id,
                    sampled,
                )
        
        # Start a transaction that continues the frontend trace
        with sentry_sdk.start_transaction(
            op="http.server",
            name=f"{req.method} /{endpoint_name}",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            sampled=sampled,
        ) as transaction:
            # Set transaction context
            transaction.set_tag("http.method", req.method)
            transaction.set_tag("http.route", f"/{endpoint_name}")
            transaction.set_tag("endpoint", endpoint_name)
            
            if user_id:
                transaction.set_tag("userId", user_id)
                sentry_sdk.set_user({"id": user_id})
            
            # Set baggage context if provided
            if baggage_header:
                transaction.set_context("baggage", {"header": baggage_header})
            
            try:
                # Execute the wrapped function
                result = func(req, *args, **kwargs)
                
                # Set status based on result
                if isinstance(result, tuple) and len(result) == 2:
                    # Response tuple: (data, status_code)
                    status_code = result[1]
                    transaction.set_tag("http.status_code", status_code)
                    if status_code >= 400:
                        transaction.set_status("internal_error" if status_code >= 500 else "invalid_argument")
                    else:
                        transaction.set_status("ok")
                else:
                    transaction.set_status("ok")
                
                return result
                
            except Exception as e:
                # Capture exception and set transaction status
                # Skip capturing ValueError - these are user input errors, not bugs
                if isinstance(e, ValueError):
                    transaction.set_status("invalid_argument")
                else:
                    transaction.set_status("internal_error")
                    sentry_sdk.capture_exception(e)
                raise
    
    return wrapper
