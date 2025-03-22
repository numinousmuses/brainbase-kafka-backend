import requests
from app.core.config import VALIDATION_ENDPOINT
import app.core.unifieddiff as unifieddiff


def validate_based_code(code: str) -> dict:
    """
    Calls the external validation endpoint to validate a full Based file.
    Expects a JSON response with "status" and, on success, "converted_code".
    """
    payload = {"code": code}
    print("=== validate_based_code ===")
    print(payload)
    try:
        r = requests.post(VALIDATION_ENDPOINT, json=payload, timeout=10)
        result = r.json()
        print("=== validate_based_code ===")
        print(result)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


def validate_based_diff(diff: str, current_content: str) -> dict:
    """
    Validate a generated Based diff with a more flexible approach that focuses on 
    resulting content correctness rather than exact diff matching.

    Steps:
      1. Apply the provided diff to the current content
      2. Validate the resulting content is valid Based code
      3. Skip the exact diff matching
      
    Returns:
      On success: {"status": "success", "converted_diff": <diff>, "updated_content": <new_content>}
      On failure: {"status": "error", "error": <error message>}
    """
    try:
        # Apply the diff locally to get the new content
        new_content = unifieddiff.apply_patch(current_content, diff)
        print("=== Applied diff successfully ===")
        
        # Skip the exact diff comparison - focus on whether the resulting content is valid
        
        # Validate the updated content via external endpoint
        payload = {"code": new_content}
        print("=== validate_based_diff ===")
        print(payload)
        try:
            r = requests.post(VALIDATION_ENDPOINT, json=payload, timeout=10)
            result = r.json()
            # On success, attach updated content and original diff to the return object
            if result.get("status") == "success":
                result["updated_content"] = new_content
                result["converted_diff"] = diff  # Keep the original diff
            return result
        except Exception as e:
            return {"status": "error", "error": f"External validation error: {str(e)}"}
            
    except Exception as e:
        print("=== Local diff application failed ===")
        return {"status": "error", "error": f"Failed to apply diff: {str(e)}"}