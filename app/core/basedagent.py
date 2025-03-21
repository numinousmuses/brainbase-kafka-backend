# app/core/basedagent.py
from openai import OpenAI
from tokencost import count_message_tokens, count_string_tokens
from app.core.config import BASED_GUIDE
import requests
import app.core.unifieddiff as unifieddiff
from schemas.basedagent import BasedAgentOutput

VALIDATION_ENDPOINT = "https://brainbase-engine-python.onrender.com/validate"

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
      
    Parameters:
      - diff: The generated unified diff string.
      - current_content: The current content of the Based file.
      
    Returns:
      On success, a dict with {"status": "success", "converted_diff": <diff>, "updated_content": <new_content>}
      On failure, a dict with {"status": "error", "error": <error message>}
    """
    try:
        # Apply the diff to the current content to get the new content.
        new_content = unifieddiff.apply_patch(current_content, diff)
        # Recompute the diff between the current content and new content.
        recomputed_diff = unifieddiff.make_patch(current_content, new_content)
        # Compare the recomputed diff with the provided diff.
        if recomputed_diff.strip() != diff.strip():
            return {"status": "error", "error": "Local diff test failed: inconsistent diff."}
    except Exception as e:
        return {"status": "error", "error": f"Local diff test exception: {str(e)}"}

    # If local test passes, validate the updated content via the external validation endpoint.
    payload = {"code": new_content}
    try:
        r = requests.post(VALIDATION_ENDPOINT, json=payload, timeout=10)
        result = r.json()
        # Optionally, attach the updated content to the success result.
        if result.get("status") == "success":
            result["updated_content"] = new_content
        return result
    except Exception as e:
        return {"status": "error", "error": f"External validation error: {str(e)}"}
    
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
    
    Inputs:
      - model: The model name (e.g., "Claude 3.7")
      - prompt: The text prompt from the user.
      - is_first_prompt: True if this is the first message in the conversation.
      - is_chat_or_composer: True if the response should be written to a .based file 
                             (i.e. handled as a based file) or False if it’s simply a plain message.

    Returns a dictionary with:
      - "output": The generated text (either full based file content, a diff, or a plain message).
      - "type": One of "based", "diff", or "response".
      - Optionally "based_filename": A filename (e.g., "sample.based") if applicable.
      - Optionally "message": A plain message if type is "response".
      
    For simulation, this function returns dummy values.
    """

    # 1) Triage the context.
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
    # triage_result should be a dict with keys like "summary", "extraction_indices", "extracted_context", and "genNewFile".
    gen_new_file = triage_result.get("genNewFile", is_first_prompt)
    
    # Check if we want a plain response (no code generation) even if triage provided context.
    plain_response_requested = triage_result.get("plain_response", False)
    
    if plain_response_requested or not is_chat_or_composer:
        # In chat mode for a plain text response.
        json_format_instructions = (
            "Return a JSON object in the following format: "
            "{ \"type\": \"response\", \"text\": <string> }."
        )
        generation_prompt = (
            f"BASED_GUIDE:\n{BASED_GUIDE}\n\n"
            f"Context summary:\n{triage_result.get('summary', '')}\n\n"
            f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
            f"Files list:\n{', '.join(triage_result.get('files_list', []))}\n\n"
            f"User prompt:\n{prompt}\n\n"
            f"{json_format_instructions}\n"
            "Please generate a plain text response that summarizes the context and answers the prompt."
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
    
    # Now we are in the code generation modes.
    if is_first_prompt or gen_new_file:
        # Compose a prompt for complete Based file generation.
        if is_chat_or_composer:
            # Composer mode: expect JSON with type "based", filename and text.
            json_format_instructions = (
                "Return a JSON object in the following format: "
                "{ \"type\": \"based\", \"filename\": <string>, \"text\": <string> }."
            )
        else:
            # Chat mode: plain text response.
            json_format_instructions = (
                "Return a JSON object in the following format: "
                "{ \"type\": \"response\", \"text\": <string> }."
            )
        generation_prompt = (
            f"Based on the following context, generate a complete and valid Based file.\n\n"
            f"BASED_GUIDE:\n{BASED_GUIDE}\n\n"
            f"Context summary:\n{triage_result.get('summary', '')}\n\n"
            f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
            f"Files list:\n{', '.join(triage_result.get('files_list', []))}\n\n"
            f"Selected based file: {selected_based_file.get('name') if selected_based_file else 'None'}\n\n"
            f"User prompt:\n{prompt}\n\n"
            f"{json_format_instructions}\n"
            "Please generate complete Based file content."
        )
        llm_conversation = [
            {"role": "system", "content": generation_prompt},
            {"role": "user", "content": "Generate complete Based file content."}
        ]
    else:
        # Compose a prompt for diff generation.
        current_based_content = selected_based_file.get("latest_content", "")
        if is_chat_or_composer:
            # Composer mode: expect JSON with type "diff", filename and text.
            json_format_instructions = (
                "Return a JSON object in the following format: "
                "{ \"type\": \"diff\", \"filename\": <string>, \"text\": <string> }."
            )
        else:
            # Chat mode: plain text response.
            json_format_instructions = (
                "Return a JSON object in the following format: "
                "{ \"type\": \"response\", \"text\": <string> }."
            )
        generation_prompt = (
            f"Based on the following context, generate a unified diff to update the existing Based file.\n\n"
            f"BASED_GUIDE:\n{BASED_GUIDE}\n\n"
            f"Context summary:\n{triage_result.get('summary', '')}\n\n"
            f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
            f"Files list:\n{', '.join(triage_result.get('files_list', []))}\n\n"
            f"Selected based file: {selected_based_file.get('name') if selected_based_file else 'None'}\n\n"
            f"Current Based file content:\n{current_based_content}\n\n"
            f"User prompt:\n{prompt}\n\n"
            f"{json_format_instructions}\n"
            "Please generate a unified diff that updates the Based file."
        )
        llm_conversation = [
            {"role": "system", "content": generation_prompt},
            {"role": "user", "content": "Generate a unified diff for updating the Based file."}
        ]
    
    # 3) Call the LLM to generate content.
    generation_response = prompt_llm_json_output(
        conversation=llm_conversation,
        model=model,
        base_url=model_base_url,
        api_key=model_ak
    )
    generated_output = generation_response.get("text")
    
    # 4) Validation and reprompt loop (up to 5 attempts)
    max_attempts = 5
    attempt = 0
    if is_first_prompt or gen_new_file:
        # We are generating a complete Based file.
        while attempt < max_attempts:
            validation_result = validate_based_code(generated_output)
            if validation_result.get("status") == "success":
                final_output = validation_result.get("converted_code", generated_output)
                break
            else:
                error_msg = validation_result.get("error", "Unknown validation error")
                # Append the error message to the prompt for re-prompting.
                llm_conversation[0]["content"] += f"\nValidation error: {error_msg}"
                generation_response = prompt_llm_json_output(
                    conversation=llm_conversation,
                    model=model,
                    base_url=model_base_url,
                    api_key=model_ak
                )
                generated_output = generation_response.get("content") or generation_response.get("output")
                attempt += 1
        else:
            return {
                "output": "Error: Unable to generate a valid Based file after multiple attempts.",
                "type": "response",
                "message": "Based file validation failed repeatedly."
            }
        # Return the successfully validated Based file.
        return {
            "output": final_output,
            "type": "based",
            "based_filename": selected_filename if selected_filename else "new_based_file.based"
        }
    else:
        # We are generating a diff update.
        current_based_content = selected_based_file.get("latest_content", "")
        # First, test the diff locally using unifieddiff.
        try:
            new_content = unifieddiff.apply_patch(current_based_content, generated_output)
            recomputed_diff = unifieddiff.make_patch(current_based_content, new_content)
            if recomputed_diff.strip() != generated_output.strip():
                raise Exception("Local diff test failed: Diff is inconsistent.")
        except Exception as e:
            return {
                "output": f"Error: Local diff test failed: {str(e)}",
                "type": "response",
                "message": "Local diff consistency check failed."
            }
        # Now validate the diff externally.
        while attempt < max_attempts:
            validation_result = validate_based_diff(generated_output, current_based_content)
            if validation_result.get("status") == "success":
                final_diff = validation_result.get("converted_diff", generated_output)
                break
            else:
                error_msg = validation_result.get("error", "Unknown diff validation error")
                # Append error message to the system prompt and re-prompt.
                llm_conversation[0]["content"] += f"\nDiff validation error: {error_msg}"
                generation_response = prompt_llm_json_output(
                    conversation=llm_conversation,
                    model=model,
                    base_url=model_base_url,
                    api_key=model_ak
                )
                generated_output = generation_response.get("content") or generation_response.get("output")
                # Re-run local diff test.
                try:
                    new_content = unifieddiff.apply_patch(current_based_content, generated_output)
                    recomputed_diff = unifieddiff.make_patch(current_based_content, new_content)
                    if recomputed_diff.strip() != generated_output.strip():
                        raise Exception("Local diff test failed on reprompt.")
                except Exception as e:
                    return {
                        "output": f"Error: Local diff test failed during reprompt: {str(e)}",
                        "type": "response",
                        "message": "Local diff consistency check failed during reprompt."
                    }
                attempt += 1
        else:
            return {
                "output": "Error: Unable to generate a valid Based diff after multiple attempts.",
                "type": "response",
                "message": "Diff validation failed repeatedly."
            }
        return {
            "output": final_diff,
            "type": "diff",
            "based_filename": selected_filename if selected_filename else "existing_based_file.based"
        }

    

def prompt_llm_json_output(
    conversation: list,
    model: str = "openai/gpt-4o",
    base_url: str = "https://openrouter.ai/api/v1",
    api_key: str = "<OPENROUTER_API_KEY>",
    extra_headers: dict = None,
    response_format: dict = {"type": "json_object"}
) -> dict:
    """
    Calls a chat completions API (compatible with OpenRouter/OpenAI) to generate a JSON-based response.
    
    Before sending the conversation, it counts the tokens using tokencost. If the total exceeds 128000 tokens,
    it removes the oldest messages (starting from the fourth message onward) until the count is below the limit.
    
    Parameters:
      - conversation: A list of messages in the format:
            [
              {"role": "developer" or "system" or "user" or "assistant", "content": "..."},
              ...
            ]
      - model: The model ID to use (default: "openai/gpt-4o").
      - base_url: The API base URL (defaults to "https://openrouter.ai/api/v1").
      - api_key: The API key for authentication (default: "<OPENROUTER_API_KEY>").
      - extra_headers: Additional headers to include in the request, e.g.:
            {
              "HTTP-Referer": "<YOUR_SITE_URL>",
              "X-Title": "<YOUR_SITE_NAME>"
            }
      - response_format: A dict specifying the desired output format from the model.
            Defaults to {"type": "json_object"} to ensure the model returns valid JSON.
            Alternatively, you could use {"type": "json_schema", "json_schema": {...}} for structured output.
    
    Returns:
      A dictionary representing the parsed JSON response message from the LLM.
    """
    # Ensure conversation token count is below the threshold.
    token_limit = 128000
    token_count = count_message_tokens(conversation, model=model)
    # Remove oldest messages after the first three until under limit.
    while token_count > token_limit and len(conversation) > 3:
        # Remove the fourth message (index 3)
        conversation.pop(3)
        token_count = count_message_tokens(conversation, model=model)
    
    # Initialize the OpenAI client.
    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )
    
    # Prepare the request parameters.
    req_params = {
        "model": model,
        "messages": conversation,
        "response_format": response_format  # Ensure JSON output.
    }
    
    # Include extra headers if provided.
    if extra_headers:
        req_params["extra_headers"] = extra_headers
    
    # Create the chat completion.
    completion = client.chat.completions.create(**req_params)
    
    # Extract the response message from the completion.
    if not completion.choices:
        return {"error": "No completion choices returned from LLM."}
    
    response_message = completion.choices[0].message
    if hasattr(response_message, "to_dict"):
        response_message = response_message.to_dict()
    else:
        response_message = dict(response_message)
    
    return response_message

def triageContext(
    selected_based_file: dict,
    prompt: str,
    conversation: list,
    chat_files_text: list,
    other_based_files: list,
    model: str,
    model_ak: str,
    model_base_url: str
) -> dict:
    """
    Triage context for the based agent.
    
    This function builds a detailed system prompt that instructs the LLM to filter and
    extract the useful context for generating Based code. It incorporates:
      - The BASED_GUIDE (imported from app/core/config.py)
      - The user prompt
      - The conversation history (formatted with line numbers)
      - The content of non-based chat files
      - Details of the selected based file (if provided)
      - A list of other based files present in the chat
     
    The desired output from the LLM should be a JSON object containing:
      - "summary": A text summary of the useful context.
      - "extraction_indices": A 2D array of line number indices indicating which portions 
                              of the context are relevant.
      - "genNewFile": A boolean indicating whether to generate a new Based file (true) 
                      or update the existing one (false).
      - "selected_tools": (Optional) A list of tools to be used in the next prompt.
      - "files_list": A list of file names to include as context.
      - "plain_response": (Optional) Boolean flag if only a plain text response is desired.
    
    This function then extracts the relevant context lines based on the provided extraction indices,
    and returns them as an additional key "extracted_context" in the output.
    """
    # Build the structured system prompt.
    system_prompt = (
        "You are the context filter for an agent in charge of generating Based code. "
        "Your job is to review the provided context and determine which parts are most useful for the next generation step. "
        "Below is the BASED_GUIDE that explains the conventions and requirements:\n\n"
        f"{BASED_GUIDE}\n\n"
        "You are provided with the following context:\n"
    )
    
    # Format conversation history with line numbers.
    formatted_conversation = "\n".join(
        [f"{i+1}: {msg['role']} - {msg['content']}" for i, msg in enumerate(conversation)]
    )
    
    # Format non-based chat files.
    formatted_chat_files = "\n".join(
        [f"{i+1}: {f['name']} - {f['content'][:100]}..." for i, f in enumerate(chat_files_text)]
    ) if chat_files_text else "None"
    
    # Format other based files.
    formatted_other_based = "\n".join(
        [f"{i+1}: {bf['name']}" for i, bf in enumerate(other_based_files)]
    ) if other_based_files else "None"
    
    # Include details of the selected based file if present.
    selected_info = f"Selected based file: {selected_based_file.get('name')}" if selected_based_file else "No selected based file."
    
    # Combine all context.
    full_context = (
        system_prompt +
        "User prompt:\n" + prompt + "\n\n" +
        "Conversation history:\n" + formatted_conversation + "\n\n" +
        "Chat text files (non-based):\n" + formatted_chat_files + "\n\n" +
        "Other based files in the chat:\n" + formatted_other_based + "\n\n" +
        selected_info + "\n\n" +
        "Based on this context, produce a JSON output with the following keys:\n"
        " - summary: a text summary of useful context\n"
        " - extraction_indices: a 2D array of line number indices indicating useful parts to be extracted from the above conversation\n"
        " - genNewFile: a boolean indicating whether a new file should be generated (true) or the current file should be updated (false)\n"
        " - files_list: a list of file names to include as context\n"
        " - plain_response: (optional) if only a plain text response is desired\n\n"
        "Return only valid JSON."
    )
    
    # Build the conversation for the LLM call.
    llm_conversation = [
        {"role": "system", "content": full_context},
        {"role": "user", "content": "Based on the context above, provide your JSON output."}
    ]
    
    # Call the LLM with our context.
    response = prompt_llm_json_output(
        conversation=llm_conversation,
        model=model,
        base_url=model_base_url,
        api_key=model_ak
    )
    
    # Parse and post-process the triage result.
    # Expected keys: "summary", "extraction_indices", "genNewFile", "files_list", "plain_response"
    # If extraction_indices is provided, extract the relevant lines from the formatted conversation.
    extraction_indices = response.get("extraction_indices", [])
    extracted_context = ""
    if extraction_indices:
        # extraction_indices is expected to be a 2D array like [[start1, end1], [start2, end2], ...]
        lines = formatted_conversation.split("\n")
        extracted_lines = []
        for index_pair in extraction_indices:
            if isinstance(index_pair, list) and len(index_pair) == 2:
                start, end = index_pair
                # Adjust indices to Python (0-indexed)
                extracted_lines.extend(lines[start-1:end])
        extracted_context = "\n".join(extracted_lines)
    
    # Include extracted context in the triage result.
    response["extracted_context"] = extracted_context
    return response
