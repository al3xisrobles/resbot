#!/usr/bin/env python3
"""
Generate OpenAPI 3.1 spec from Pydantic response schemas.
Run from functions/ directory: python scripts/generate_openapi.py
Output: ../src/lib/generated/openapi.json
"""
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.response_schemas import (
    ApiResponse,
    CalendarData,
    GeminiSearchData,
    MeData,
    OnboardingData,
    SearchData,
    SlotsData,
    SnipeResultData,
    JobCreatedData,
    JobUpdatedData,
    JobCancelledData,
    SummaryData,
    VenueDetailData,
    VenueLinksData,
    VenuePaymentRequirementData,
    ReservationCreatedData,
    TrendingRestaurantItem,
    AccountStatusData,
    PaymentMethodUpdateData,
    DisconnectData,
)


def rewrite_refs(obj, defs_map):
    """Rewrite $ref from #/$defs/X to #/components/schemas/X."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            if ref.startswith("#/$defs/"):
                name = ref.replace("#/$defs/", "")
                obj["$ref"] = f"#/components/schemas/{name}"
            elif ref.startswith("#/components/schemas/"):
                pass  # Already correct
            return
        for v in obj.values():
            rewrite_refs(v, defs_map)
    elif isinstance(obj, list):
        for item in obj:
            rewrite_refs(item, defs_map)


def get_schema_for_model(model_class):
    """Get JSON schema for a Pydantic model, suitable for OpenAPI components."""
    schema = model_class.model_json_schema()
    defs = schema.pop("$defs", {})
    # Rewrite $ref in schema and defs to use components path
    rewrite_refs(schema, defs)
    for def_schema in defs.values():
        rewrite_refs(def_schema, {})
    return {"schema": schema, "definitions": defs}


def build_openapi_spec():
    """Build OpenAPI 3.1 specification."""
    # Map of response data models for success responses
    data_models = {
        "MeData": MeData,
        "TrendingRestaurantItem": TrendingRestaurantItem,  # Used by ApiResponse_TrendingRestaurantsData
        "OnboardingData": OnboardingData,
        "VenueDetailData": VenueDetailData,
        "VenueLinksData": VenueLinksData,
        "VenuePaymentRequirementData": VenuePaymentRequirementData,
        "SearchData": SearchData,
        "CalendarData": CalendarData,
        "SlotsData": SlotsData,
        "ReservationCreatedData": ReservationCreatedData,
        "GeminiSearchData": GeminiSearchData,
        "SummaryData": SummaryData,
        "SnipeResultData": SnipeResultData,
        "JobCreatedData": JobCreatedData,
        "JobUpdatedData": JobUpdatedData,
        "JobCancelledData": JobCancelledData,
        "AccountStatusData": AccountStatusData,
        "PaymentMethodUpdateData": PaymentMethodUpdateData,
        "DisconnectData": DisconnectData,
        "TrendingRestaurantsData": list[TrendingRestaurantItem],
    }

    components_schemas = {}
    for name, model_class in data_models.items():
        if hasattr(model_class, "model_json_schema"):
            result = get_schema_for_model(model_class)
            components_schemas[name] = result["schema"]
            for def_name, def_schema in result["definitions"].items():
                if def_name not in components_schemas:
                    components_schemas[def_name] = def_schema

    # ApiResponse wrapper schema
    api_response_schema = ApiResponse.model_json_schema()
    api_defs = api_response_schema.pop("$defs", {})
    for def_name, def_schema in api_defs.items():
        if def_name not in components_schemas:
            components_schemas[def_name] = def_schema

    # Build paths - simplified structure for schema generation
    paths = {
        "/me": {
            "get": {
                "summary": "Get user session data",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_MeData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/venue": {
            "get": {
                "summary": "Get venue details",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_VenueDetailData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/venue_links": {
            "get": {
                "summary": "Get venue links",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_VenueLinksData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/check_venue_payment_requirement": {
            "get": {
                "summary": "Check venue payment requirement",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_VenuePaymentRequirementData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/search": {
            "get": {
                "summary": "Search restaurants",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_SearchData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/search_map": {
            "get": {
                "summary": "Search restaurants by map",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_SearchData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/calendar": {
            "get": {
                "summary": "Get calendar availability",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_CalendarData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/slots": {
            "get": {
                "summary": "Get available slots",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_SlotsData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/reservation": {
            "post": {
                "summary": "Create reservation",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_ReservationCreatedData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/gemini_search": {
            "post": {
                "summary": "AI-powered reservation info",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_GeminiSearchData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/climbing": {
            "get": {
                "summary": "Get climbing restaurants",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_TrendingRestaurantsData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/top_rated": {
            "get": {
                "summary": "Get top-rated restaurants",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_TrendingRestaurantsData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/start_resy_onboarding": {
            "post": {
                "summary": "Start Resy onboarding",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_OnboardingData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/resy_account": {
            "get": {
                "summary": "Get Resy account status",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_AccountStatusData"
                                }
                            }
                        },
                    },
                },
            },
            "post": {
                "summary": "Update payment method",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_PaymentMethodUpdateData"
                                }
                            }
                        },
                    },
                },
            },
            "delete": {
                "summary": "Disconnect Resy account",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_DisconnectData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/summarize_snipe_logs": {
            "post": {
                "summary": "Summarize snipe logs",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_SummaryData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/create_snipe": {
            "post": {
                "summary": "Create snipe job",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_JobCreatedData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/update_snipe": {
            "post": {
                "summary": "Update snipe job",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_JobUpdatedData"
                                }
                            }
                        },
                    },
                },
            },
        },
        "/cancel_snipe": {
            "post": {
                "summary": "Cancel snipe job",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ApiResponse_JobCancelledData"
                                }
                            }
                        },
                    },
                },
            },
        },
    }

    # Build ApiResponse wrappers for each data type
    from typing import get_origin, get_args

    for name, model_class in data_models.items():
        if name == "TrendingRestaurantsData":
            # Special case for list
            from pydantic import TypeAdapter

            adapter = TypeAdapter(list[TrendingRestaurantItem])
            inner_schema = adapter.json_schema()
        elif hasattr(model_class, "model_json_schema"):
            inner_schema = {"$ref": f"#/components/schemas/{name}"}
        else:
            continue

        wrapper_name = f"ApiResponse_{name}"
        components_schemas[wrapper_name] = {
            "type": "object",
            "required": ["success"],
            "properties": {
                "success": {"type": "boolean"},
                "data": inner_schema if name != "TrendingRestaurantsData" else {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/TrendingRestaurantItem"},
                },
                "error": {"type": "string"},
            },
        }

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Resy Bot API",
            "version": "1.0.0",
            "description": "API for Resy Bot - restaurant reservation automation",
        },
        "paths": paths,
        "components": {
            "schemas": components_schemas,
        },
    }

    return spec


def main():
    """Generate OpenAPI spec and write to file."""
    spec = build_openapi_spec()

    output_dir = Path(__file__).resolve().parent.parent.parent / "src" / "lib" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "openapi.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)

    print("Generated OpenAPI spec at", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
