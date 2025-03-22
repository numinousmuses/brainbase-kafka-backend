import uuid
from datetime import datetime
from app.core.config import BASED_GUIDE
import app.core.unifieddiff as unifieddiff

# Import from our local package modules
from .validation import validate_based_code, validate_based_diff
from .llm import prompt_llm_json_output
from .triage import triageContext

def handle_new_message(
    model: str, 
    model_ak: str, 
    model_base_url: str, 
    selected_filename: str,
    selected_based_file: dict, 
    prompt: str, 
    is_first_prompt: bool, 
    is_chat_or_composer: bool, 
    conversation: list, 
    chat_files_text: list, 
    other_based_files: list
) -> dict:
    """
    Process a new message using the Based agent logic.
    
    Returns a dict with keys like:
      - "output": The generated text (complete .based content, a diff, or a plain message)
      - "type": "based", "diff", or "response"
      - Optionally "based_filename" if type is "based" or "diff"
      - Optionally "message" if type is "response"
    """

    print('=== handle_new_message ===')
    print({
        "model": model,
        "model_ak": model_ak,
        "model_base_url": model_base_url,
        "selected_filename": selected_filename,
        "selected_based_file": selected_based_file,
        "prompt": prompt,
        "is_first_prompt": is_first_prompt,
        "is_chat_or_composer": is_chat_or_composer,
        "conversation": conversation,
        "chat_files_text": chat_files_text,
        "other_based_files": other_based_files
    })

    # 1) Triage the context
    triage_result = triageContext(
        selected_based_file=selected_based_file,
        prompt=prompt,
        conversation=conversation,
        chat_files_text=chat_files_text,
        other_based_files=other_based_files,
        model=model,
        model_ak=model_ak,
        model_base_url=model_base_url
    )
    gen_new_file = triage_result.get("genNewFile", is_first_prompt)
    plain_response_requested = triage_result.get("plain_response", False)

    # 2) If plain response or not composer, just return text
    if plain_response_requested or not is_chat_or_composer:
        json_format_instructions = (
            "Return a JSON object in the following format: "
            "{ \"type\": \"response\", \"text\": <string> }."
        )
        generation_prompt = (
            f"Context summary:\n{triage_result.get('summary', '')}\n\n"
            f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
            f"Files list:\n{', '.join(triage_result.get('files_list', []))}\n\n"
            f"User prompt:\n{prompt}\n\n"
            f"{json_format_instructions}\n"
            "Generate a plain text response summarizing the context and addressing the prompt."
        )
        llm_conversation = [
            {"role": "system", "content": generation_prompt},
            {"role": "user", "content": "Generate plain text response."}
        ]
        generation_response = prompt_llm_json_output(
            conversation=llm_conversation,
            model=model,
            base_url=model_base_url,
            api_key=model_ak
        )


        generated_text = generation_response.get("text") or generation_response.get("output")
        return {
            "type": "response",
            "message": generated_text
        }

    # 3) Otherwise, we’re generating or updating Based code
    if is_first_prompt or gen_new_file:
        # Generate a brand-new Based file
        return _generate_whole_based_file(
            model, model_ak, model_base_url,
            selected_filename, prompt, triage_result
        )
    else:
        # Generate a diff to update an existing Based file
        return _generate_based_diff(
            model, model_ak, model_base_url,
            selected_filename, prompt, selected_based_file, triage_result
        )


def _generate_whole_based_file(
    model: str,
    model_ak: str,
    model_base_url: str,
    selected_filename: str,
    prompt: str,
    triage_result: dict
) -> dict:
    """
    Helper for handle_new_message: create a brand new .based file.
    """
    # Build the system prompt
    json_format_instructions = (
        "Return a JSON object in the following format: "
        "{ \"type\": \"based\", \"filename\": <string>, \"text\": <string> }."
    )
    generation_prompt = (
        f"Based on the following context, generate a complete and valid Based file.\n\n"
        f"BASED_GUIDE:\n{BASED_GUIDE}\n\n"
        f"Context summary:\n{triage_result.get('summary', '')}\n\n"
        f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
        f"Files list:\n{', '.join(triage_result.get('files_list', []))}\n\n"
        f"User prompt:\n{prompt}\n\n"
        f"{json_format_instructions}\n"
        "Please generate the complete .based file content."
    )
    llm_conversation = [
        {"role": "system", "content": generation_prompt},
        {"role": "user", "content": "Generate complete Based file content."}
    ]

    # Attempt up to 5 times to validate
    max_attempts = 5
    attempt = 0
    generated_output = None
    final_output = None

    while attempt < max_attempts:
        generation_response = prompt_llm_json_output(
            conversation=llm_conversation,
            model=model,
            base_url=model_base_url,
            api_key=model_ak
        )
        generated_output = generation_response.get("text") or generation_response.get("output")

        validation_result = validate_based_code(generated_output)
        if validation_result.get("status") == "success":
            final_output = validation_result.get("converted_code", generated_output)
            break
        else:
            error_msg = validation_result.get("error", "Unknown validation error")
            llm_conversation[0]["content"] += f"\nValidation error: {error_msg}"
            attempt += 1

    if final_output is None:
        return {
            "output": "Error: Unable to generate a valid Based file after multiple attempts.",
            "type": "response",
            "message": "Based file validation failed repeatedly."
        }

    return {
        "output": final_output,
        "type": "based",
        "based_filename": selected_filename if selected_filename else "new_based_file.based"
    }


def _generate_based_diff(
    model: str,
    model_ak: str,
    model_base_url: str,
    selected_filename: str,
    prompt: str,
    selected_based_file: dict,
    triage_result: dict
) -> dict:
    """
    Helper for handle_new_message: generate a diff to update an existing .based file.
    """
    current_based_content = selected_based_file.get("latest_content", "")

    # Build the system prompt
    json_format_instructions = (
        "Return a JSON object in the following format: "
        "{ \"type\": \"diff\", \"filename\": <string>, \"text\": <string> }."
    )
    generation_prompt = (
        f"Based on the following context, generate a unified diff to update the existing Based file.\n\n"
        f"BASED_GUIDE:\n{BASED_GUIDE}\n\n"
        f"Context summary:\n{triage_result.get('summary', '')}\n\n"
        f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
        f"Files list:\n{', '.join(triage_result.get('files_list', []))}\n\n"
        f"Current Based file content:\n{current_based_content}\n\n"
        f"User prompt:\n{prompt}\n\n"
        f"{json_format_instructions}\n"
        "Please generate a unified diff that updates the Based file."
    )
    llm_conversation = [
        {"role": "system", "content": generation_prompt},
        {"role": "user", "content": "Generate a unified diff for updating the Based file."}
    ]

    max_attempts = 5
    attempt = 0
    generated_diff = None

    while attempt < max_attempts:
        generation_response = prompt_llm_json_output(
            conversation=llm_conversation,
            model=model,
            base_url=model_base_url,
            api_key=model_ak
        )
        generated_diff = generation_response.get("text") or generation_response.get("output")

        # Local check
        try:
            new_content = unifieddiff.apply_patch(current_based_content, generated_diff)
            recomputed_diff = unifieddiff.make_patch(current_based_content, new_content)
            if recomputed_diff.strip() != generated_diff.strip():
                raise Exception("Local diff test failed: Diff is inconsistent.")
        except Exception as e:
            # Immediately fail this attempt
            llm_conversation[0]["content"] += f"\nLocal diff consistency check failed: {str(e)}"
            attempt += 1
            continue

        # External validation
        validation_result = validate_based_diff(generated_diff, current_based_content)
        if validation_result.get("status") == "success":
            final_diff = validation_result.get("converted_diff", generated_diff)
            return {
                "output": final_diff,
                "type": "diff",
                "based_filename": selected_filename if selected_filename else "existing_based_file.based"
            }
        else:
            error_msg = validation_result.get("error", "Unknown diff validation error")
            llm_conversation[0]["content"] += f"\nDiff validation error: {error_msg}"
            attempt += 1

    return {
        "output": "Error: Unable to generate a valid Based diff after multiple attempts.",
        "type": "response",
        "message": "Diff validation failed repeatedly."
    }