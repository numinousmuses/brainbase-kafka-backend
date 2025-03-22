from openai import OpenAI
import json

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
    
    Returns a dictionary representing the parsed JSON response message from the LLM.
    """
    # token_limit = 128000
    # token_count = count_message_tokens(conversation, model=model)
    # # Remove oldest messages after the first three until under limit.
    # while token_count > token_limit and len(conversation) > 3:
    #     conversation.pop(3)
    #     token_count = count_message_tokens(conversation, model=model)

    # Initialize the OpenAI client.
    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )

    req_params = {
        "model": model,
        "messages": conversation,
        "response_format": response_format,  # Ensure JSON output
    }
    if extra_headers:
        req_params["extra_headers"] = extra_headers

    # Create the chat completion
    completion = client.chat.completions.create(**req_params)

    # print("completion:", completion)
    
    # Extract the response message from the completion
    if not completion.choices:
        return {"error": "No completion choices returned from LLM."}
    response_message = completion.choices[0].message

    # print()
    # print("response_format:", response_format)
    # print("response_message:", response_message)


    
    # If the response is an object with to_dict(), convert to a dict
    if hasattr(response_message, "to_dict"):
        # parsed_output = json.loads(response_message)
        # print("parsed_output:", parsed_output)
        response_message = response_message.to_dict()
        print("LLM Generated Ouput")
        
        
    else:
        response_message = dict(response_message)

    return response_message
