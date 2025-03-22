from app.core.config import BASED_GUIDE
from .llm import prompt_llm_json_output

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
    Builds a detailed system prompt that instructs the LLM to filter and
    extract the useful context for generating Based code.

    Returns:
      A dict with keys like:
       - summary
       - extraction_indices
       - genNewFile
       - files_list
       - plain_response
       - extracted_context (populated after we parse extraction_indices)
    """
    system_prompt = (
        "You are the context filter for an agent in charge of generating Based code. "
        "Your job is to review the provided context and determine which parts are most useful "
        "for the next generation step.\n\n"
        f"BASED_GUIDE:\n{BASED_GUIDE}\n\n"
        "You are provided with the following context:\n"
    )

    # 1) Format conversation with line numbers
    formatted_conversation = "\n".join(
        [f"{i+1}: {msg['role']} - {msg['content']}" for i, msg in enumerate(conversation)]
    )

    # 2) Format non-based chat files
    formatted_chat_files = (
        "\n".join(
            [f"{i+1}: {f['name']} - {f['content']}" for i, f in enumerate(chat_files_text)]
        )
        if chat_files_text else "None"
    )

    # 3) Format other .based files
    formatted_other_based = "None"
    if other_based_files:
        lines = []
        for i, bf in enumerate(other_based_files, start=1):
            latest_content = bf.get("latest_content", "")
            lines.append(
                f"{i}: Name: {bf['name']}\nLatest content:\n{latest_content}\n"
            )
        formatted_other_based = "\n".join(lines)

    # 4) Selected based file
    if selected_based_file:
        selected_info = (
            f"Selected based file: {selected_based_file.get('name')}\n"
            f"Full content:\n{selected_based_file.get('latest_content', '')}\n"
        )
    else:
        selected_info = "No selected based file."

    # Combine everything
    full_context = (
        system_prompt +
        f"User prompt:\n{prompt}\n\n"
        f"Conversation history:\n{formatted_conversation}\n\n"
        f"Chat text files (non-based):\n{formatted_chat_files}\n\n"
        f"Other based files:\n{formatted_other_based}\n\n"
        f"{selected_info}\n\n"
        "Based on this context, produce a JSON output with the following keys:\n"
        "genNewFile should only be true if generating a new file from SCRATCH, if editing a file, a diff needs to be made, so genNewFile must be FALSE\n"
        "plain_response must be a boolean representing whether a simple chat response is to be made, or a Based file or diff needs to be generated. if the latter two, plain_response MUST be false\n"
        " - summary\n - extraction_indices\n - genNewFile\n - files_list\n - plain_response\n\n"
        "Return only valid JSON."
    )

    llm_conversation = [
        {"role": "system", "content": full_context},
        {"role": "user", "content": "Based on the context above, provide your JSON output."}
    ]

    response = prompt_llm_json_output(
        conversation=llm_conversation,
        model=model,
        base_url=model_base_url,
        api_key=model_ak
    )

    # Post-process extraction_indices
    extraction_indices = response.get("extraction_indices", [])
    extracted_context = ""
    if extraction_indices:
        lines = formatted_conversation.split("\n")
        extracted_lines = []
        for pair in extraction_indices:
            if isinstance(pair, list) and len(pair) == 2:
                start, end = pair
                extracted_lines.extend(lines[start-1:end])
        extracted_context = "\n".join(extracted_lines)

    response["extracted_context"] = extracted_context
    return response