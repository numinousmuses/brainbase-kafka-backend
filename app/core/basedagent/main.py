import uuid
from datetime import datetime
from app.core.config import BASED_GUIDE, UNIFIED_DIFF, VALIDATION_FUNCTION
import app.core.unifieddiff as unifieddiff
import json
import json_repair
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

    print('\n\n\n\n\n\n\n\n\n\ntriage_result')
    print(triage_result)
    print('\n\n\n\n\n\n\n\n\n')

    triage_result = triage_result["content"]
    triage_result = json_repair.loads(triage_result)
    
    gen_new_file = triage_result.get("genNewFile", is_first_prompt)
    plain_response_requested = triage_result.get("plain_response", False)

    # 2) If plain response or not composer, just return text
    if plain_response_requested or not is_chat_or_composer:
        print('returning plain response')
        json_format_instructions = (
            "Return a JSON object in the following format: "
            "{ \"text\": <string> }."
        )
        generation_prompt = (
            f"Context summary:\n{triage_result.get('summary', '')}\n\n"
            f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
            f"Files list:\n{', '.join(triage_result.get('files_list', []))}\n\n"
            f"User prompt:\n{prompt}\n\n"
            f"Past conversation:\n{conversation}\n\n"
            f"Selected .based file tostring:\n{str(selected_based_file)}\n\n"
            f"{json_format_instructions}\n"
            "Generate a plain text response summarizing addressing the prompt."
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


        generated_text = generation_response.get("content")

        generated_text_obj = json_repair.loads(generated_text)
        generated_text = generated_text_obj.get("text")
         
        return {
            "type": "response",
            "message": generated_text
        }

    # 3) Otherwise, we’re generating or updating Based code
    if is_first_prompt or gen_new_file:
        print("=== _generate_whole_based_file ===")
        # Generate a brand-new Based file
        return _generate_whole_based_file(
            model, model_ak, model_base_url,
            selected_filename, prompt, triage_result
        )
    else:
        # Generate a diff to update an existing Based file
        print("=== _generate_based_diff ===")
        print(triage_result)
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
        generated_output = generation_response.get("content") or generation_response.get("text") or generation_response.get("output")

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
    Uses a more flexible approach to diff validation.
    """
    current_based_content = selected_based_file.get("latest_content", "")

    # Build a clearer system prompt with examples
    json_format_instructions = (
        "Return a JSON object in the following format, where text is the diff to be applied to the current Based file: "
        "{ \"type\": \"diff\", \"filename\": <string>, \"text\": <string> }."
    )
    
    example_diff_basic = (
        "--- file.based\n"
        "+++ file.based\n"
        "@@ -5,6 +5,9 @@\n"
        " \texisting line\n"
        " \texisting line\n"
        "+\tnew line 1\n"
        "+\tnew line 2\n"
        "+\tnew line 3\n"
        " \texisting line\n"
        " \texisting line\n"
    )

    example_diff_replace = (
        "--- file.based\n"
        "+++ file.based\n"
        "@@ -10,7 +10,8 @@\n"
        " \tunchanged line\n"
        " \tunchanged line\n"
        "-\told line to remove\n"
        "+\tnew replacement line\n"
        "+\tadditional new line\n"
        " \tunchanged line\n"
        " \tunchanged line\n"
    )

    example_diff_multiple = (
        "--- file.based\n"
        "+++ file.based\n"
        "@@ -5,6 +5,7 @@\n"
        " \tcontext line\n"
        " \tcontext line\n"
        "+\tnew line\n"
        " \tcontext line\n"
        "@@ -20,7 +21,6 @@\n"
        " \tmore context\n"
        " \tmore context\n"
        "-\tline to delete\n"
        " \tmore context\n"
        " \tmore context\n"
    )

    generation_prompt = (
        f"Based on the following context, generate a diff to update the existing Based file.\n\n"
        f"BASED_GUIDE:\n{BASED_GUIDE}\n\n"
        f"Context summary:\n{triage_result.get('summary', '')}\n\n"
        f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
        f"Files list:\n{', '.join(triage_result.get('files_list', []))}\n\n"
        f"Current Based file name:\n{selected_filename}\n\n"
        f"Current Based file content:\n{current_based_content}\n\n"
        f"User prompt:\n{prompt}\n\n"
        f"IMPORTANT: Generate a proper unified diff format. Here are valid examples:\n\n"
        f"Example 1 - Adding new lines:\n{example_diff_basic}\n\n"
        f"Example 2 - Replacing lines:\n{example_diff_replace}\n\n"
        f"Example 3 - Multiple changes:\n{example_diff_multiple}\n\n"
        f"RULES FOR DIFF GENERATION:\n"
        f"1. Do NOT modify existing code unless absolutely necessary\n"
        f"2. Add new functionality by adding new lines in appropriate places\n"
        f"3. Maintain the exact same indentation style used in the original file\n"
        f"4. Only include the changed lines and minimal context in your diff\n"
        f"5. Make sure your diff applies cleanly to the original file\n"
        f"6. Always include both '---' and '+++' lines in your diff\n"
        f"7. Use proper unified diff headers with correct line numbers\n\n"
        f"{json_format_instructions}\n"
        "Please generate a diff that updates the Based file according to the user's request."
    )

    
    llm_conversation = [
        {"role": "system", "content": generation_prompt},
        {"role": "user", "content": "Generate a diff for updating the Based file."}
    ]

    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        generation_response = prompt_llm_json_output(
            conversation=llm_conversation,
            model=model,
            base_url=model_base_url,
            api_key=model_ak
        )
        print("\n\n\n\n\n\nGenerated Diff\n\n\n\n\n\n")
        generated_diff = generation_response.get("content")
        # print(generated_diff)
        
        # Parse the JSON to extract the "text" parameter
        try:
            generated_diff_obj = json_repair.loads(generated_diff)
            generated_diff = generated_diff_obj.get("text")
            if not generated_diff:
                raise ValueError("Missing 'text' field in JSON response")
            print("\n\n\n\n\n\n\nSuccessfully parsed diff\n\n\n\n\n\n\n")
            # print(generated_diff)
        except Exception as e:
            llm_conversation[0]["content"] += f"\nError parsing JSON: {str(e)}"
            print("\n\n\n\n\n\n\nFailed to parse diff\n\n\n\n\n\n\n")
            attempt += 1
            continue

        # Skip the strict local check, just make sure the diff can be applied
        try:
            new_content = unifieddiff.apply_patch(current_based_content, generated_diff)
            print("\n\n\n\n\n\n\nSuccessfully applied local diff patch\n\n\n\n\n\n\n")
            print("new_content:", new_content)
            
            # External validation of the resulting content
            validation_result = validate_based_diff(generated_diff, current_based_content)
            print(f"\n\n\n\n\n\n\Validation result {validation_result} \n\n\n\n\n\n\n")
            if validation_result.get("status") == "success":
                final_diff = validation_result.get("converted_diff", generated_diff)
                return {
                    "output": final_diff,
                    "type": "diff",
                    "based_filename": selected_filename if selected_filename else "existing_based_file.based"
                }
            else:
                error_msg = validation_result.get("error", "Unknown diff validation error")
                llm_conversation[0]["content"] += f"\nDiff validation error: {error_msg}\n"
                llm_conversation[0]["content"] += "Please try again with a simpler diff that maintains the same structure as the original file."
                attempt += 1
                
        except Exception as e:
            # If the diff can't be applied at all, try again
            llm_conversation[0]["content"] += f"\nFailed to apply diff: {str(e)}\n"
            llm_conversation[0]["content"] += "Please generate a simpler, cleaner diff that follows unified diff format."
            attempt += 1
            continue

    return {
        "output": "Error: Unable to generate a valid Based diff after multiple attempts.",
        "type": "response",
        "message": "Diff validation failed repeatedly."
    }