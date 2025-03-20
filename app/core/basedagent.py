# app/core/basedagent.py
from openai import OpenAI

def handle_new_message(model: str, prompt: str, is_first_prompt: bool, is_chat_or_composer: bool, conversation: list, chat_files_text: list):
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
      
    Example usage:
      >>> conv = [
      ...     {"role": "system", "content": "You are a helpful assistant."},
      ...     {"role": "user", "content": "What is the meaning of life?"}
      ... ]
      >>> response = prompt_llm_json_output(conv, api_key="YOUR_API_KEY", base_url="https://openrouter.ai/api/v1")
      >>> print(response)
    """
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