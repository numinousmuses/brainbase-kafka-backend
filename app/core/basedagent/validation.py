import requests
from app.core.config import VALIDATION_ENDPOINT
import app.core.unifieddiff as unifieddiff


def validate_based_code(code: str) -> dict:
    """
    Calls the external validation endpoint to validate a full Based file.
    Expects a JSON response with "status" and, on success, "converted_code".
    """
    payload = {"code": code}
    try:
        r = requests.post(VALIDATION_ENDPOINT, json=payload, timeout=10)
        result = r.json()
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


def validate_based_diff(diff: str, current_content: str) -> dict:
    """
    Validate a generated Based diff by first verifying it locally using unifieddiff,
    then validating the updated content via an external validation endpoint.

    Steps:
      1. Apply the provided diff to the current content.
      2. Recompute the diff between the original and updated content.
      3. If the recomputed diff does not match the provided diff (after stripping whitespace),
         return an error.
      4. If the diff passes the local test, send the updated content to the validation endpoint.
      
    Returns:
      On success: {"status": "success", "converted_diff": <diff>, "updated_content": <new_content>}
      On failure: {"status": "error", "error": <error message>}
    """
    try:
        # Apply the diff locally.
        new_content = unifieddiff.apply_patch(current_content, diff)
        recomputed_diff = unifieddiff.make_patch(current_content, new_content)
        if recomputed_diff.strip() != diff.strip():
            return {"status": "error", "error": "Local diff test failed: inconsistent diff."}
    except Exception as e:
        return {"status": "error", "error": f"Local diff test exception: {str(e)}"}

    # Validate the updated content via external endpoint.
    payload = {"code": new_content}
    try:
        r = requests.post(VALIDATION_ENDPOINT, json=payload, timeout=10)
        result = r.json()
        # On success, attach updated content to the return object.
        if result.get("status") == "success":
            result["updated_content"] = new_content
        return result
    except Exception as e:
        return {"status": "error", "error": f"External validation error: {str(e)}"}