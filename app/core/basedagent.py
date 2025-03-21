# app/core/basedagent.py
from openai import OpenAI
from tokencost import count_message_tokens, count_string_tokens
from app.core.config import BASED_GUIDE

def handle_new_message(
        model: str, 
        model_ak: str, 
        model_base_url: str, 
        selected_filename: str,
        selected_based_file: str, 
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
    # (Simulated logic)
    if is_chat_or_composer:
        if is_first_prompt:
            # Generate a new based file.
            return {
                "output": "Generated based file content for first prompt.",
                "type": "based",
                "based_filename": "new_based_file.based"
            }
        else:
            # Not first prompt: generate a diff update.
            return {
                "output": "Generated diff content for update.",
                "type": "diff",
                "based_filename": "existing_based_file.based"
            }
    else:
        # Plain message response.
        return {
            "output": "Plain response message.",
            "type": "response",
            "message": "This is a plain text response from the agent."
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
    is_first_prompt: bool,
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
      - "extraction_indices": A 2D array of indices (line numbers) indicating which portions of the context are relevant.
      - "genNewFile": A boolean indicating whether to generate a new Based file (True) or edit the existing one (False).
      - "selected_tools": A list of tools to be used in the next prompt.
      - "files_list": A list of file names to consider.
    
    The function then calls prompt_llm_json_output with the constructed conversation and returns the parsed JSON response.
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
        " - extraction_indices: a 2D array of line number indices indicating useful parts to be extracted from this prompt and included in the prompt for the generator agent\n"
        " - genNewFile: a boolean indicating whether a new file should be generated (true) or the current file should be updated (false)\n"
        " - files_list: a list of file names to include as context\n\n"
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
    
    return response
