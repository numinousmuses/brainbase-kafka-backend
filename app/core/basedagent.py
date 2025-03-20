# app/core/basedagent.py

def handle_new_message(model: str, prompt: str, is_first_prompt: bool, is_chat_or_composer: bool):
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
