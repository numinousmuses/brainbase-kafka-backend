import uuid
from datetime import datetime
from app.core.config import BASED_GUIDE, UNIFIED_DIFF, VALIDATION_FUNCTION, USER_MESSAGE_BASED_GUIDELINES, TOOLS_DOCUMENTATION
import app.core.unifieddiff as unifieddiff
import json
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
    max_attempts = 5
    attempt = 0
    triage_result = None

    while attempt < max_attempts:
        try:
            triage_response = triageContext(
                selected_based_file=selected_based_file,
                prompt=prompt,
                conversation=conversation,
                chat_files_text=chat_files_text,
                other_based_files=other_based_files,
                model=model,
                model_ak=model_ak,
                model_base_url=model_base_url
            )
            
            content = triage_response["content"]
            triage_result = json.loads(content)
            # Successfully parsed the JSON
            break
        except json.JSONDecodeError as e:
            # Handle JSON parsing error by retrying
            print(f"JSON parsing error (attempt {attempt+1}): {str(e)}")
            attempt += 1
            if attempt >= max_attempts:
                return {
                    "type": "response",
                    "message": f"Error: Failed to process request after {max_attempts} attempts due to JSON parsing issues."
                }
    
    print('\n\n\n\n\n\n\n\n\n\ntriage_result')
    print(triage_result)
    print('\n\n\n\n\n\n\n\n\n')

    # 2) Run the Tool Context Agent to see which tools are relevant
    tool_agent_result = tool_context_agent(
        prompt=prompt,
        triage_result=triage_result,
        conversation=conversation,
        tools_documentation=TOOLS_DOCUMENTATION,   # reference wherever you store this
        model=model,
        model_ak=model_ak,
        model_base_url=model_base_url
    )
    relevant_tools = tool_agent_result.get("tools", [])
    print("\n\nTool Agent returned these relevant tools:", relevant_tools, "\n\n")

    gen_new_file = triage_result["genNewFile"]
    plain_response_requested = triage_result["plain_response"]

    if is_first_prompt or gen_new_file:
        print("=== _generate_whole_based_file ===")
        # Generate a brand-new Based file
        return _generate_whole_based_file(
            model, model_ak, model_base_url,
            selected_filename, prompt, triage_result, 
            relevant_tools
        )

    # 2) If plain response or not composer, just return text
    elif plain_response_requested or not is_chat_or_composer:
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
        
        max_attempts = 5
        attempt = 0
        generated_text = None
        
        while attempt < max_attempts:
            try:
                generation_response = prompt_llm_json_output(
                    conversation=llm_conversation,
                    model=model,
                    base_url=model_base_url,
                    api_key=model_ak
                )
                
                content = generation_response.get("content")
                generated_text_obj = json.loads(content)
                generated_text = generated_text_obj.get("text")
                # Successfully parsed the JSON
                break
            except json.JSONDecodeError as e:
                # Handle JSON parsing error by retrying with updated prompt
                print(f"JSON parsing error (attempt {attempt+1}): {str(e)}")
                llm_conversation[0]["content"] += (
                    f"\n\nYour previous response could not be parsed as JSON. "
                    f"Please ensure you return a valid JSON object exactly in this format: {{\"text\": \"your response here\"}}."
                )
                attempt += 1
                if attempt >= max_attempts:
                    return {
                        "type": "response",
                        "message": f"Error: Failed to generate a valid response after {max_attempts} attempts due to JSON parsing issues."
                    }

        print("\n\n\n\n\n\n\n\n")
        print(generated_text_obj)
        print("\n\n\n\n\n\n\n\n")
         
        return {
            "type": "response",
            "message": generated_text
        }
    
    else:
        # Generate a diff to update an existing Based file
        print("=== _generate_based_diff ===")
        print(triage_result)
        return _generate_based_diff(
            model, model_ak, model_base_url,
            selected_filename, prompt, selected_based_file, triage_result, 
            relevant_tools
        )


def _generate_whole_based_file(
    model: str,
    model_ak: str,
    model_base_url: str,
    selected_filename: str,
    prompt: str,
    triage_result: dict,
    relevant_tools: list
) -> dict:
    """
    Helper for handle_new_message: create a brand new .based file.
    """

    # This step aggregates the full documentation text for each relevant tool.
    relevant_docs = []
    for tool_name in relevant_tools:
        for t in TOOLS_DOCUMENTATION:
            if t["name"] == tool_name:
                # Use short description or the full 'docs' to pass along
                relevant_docs.append(f"Tool Name: {t['name']}\nFunction: {t['function']}\nDocs:\n{t['docs']}")
                break

    combined_tool_docs = "\n\n".join(relevant_docs)

    # Build the system prompt
     # Build the system prompt
    json_format_instructions = (
        "Return a JSON object in the following format: Your text file must begin with a based loop block, and have one or more until blocks."
        "{ \"type\": \"based\", \"filename\": <string>, \"text\": <string> }."
    )
    generation_prompt = (
        f"Based on the following context, generate a complete and valid Based file. It is important to note that based may resemble python, but they are not the same. Based is COMPILED into python. Meaning that while loops are not valid and are broken code. based code is compiled into python, but not vice versa.    Based uses a loop until, whereas python normally has while loops. It is imperative you abide by this distrinction.\n\n"
        f"BASED_GUIDE: the following is the guide on how to write a based file, examples included. IT IS IMPERATIVE you conform to this guide and the format described. An important thing to note about based is that your conditions are all strings, as you see in the examples. You must follow the loop until paradigm, as the examples demonstrate. If you do not follow this, the agent will not be compatible with the based engine, and this will cause damages to the businesses relying on these agents. People's livelihoods depend on the generated agents. It is immoral for you to follow a different format.  \n{BASED_GUIDE}\n\n IT IS IMPERATIVE you conform to this guide and the format described. An important thing to note about based is that your conditions are all strings, as you see in the examples. Your generated code's most outside layers must be loop and until. Meaning at the top level, you MUST have a loop and until/END BASED_GUIDE/\n\n"
        f"Context summary:\n{triage_result.get('summary', '')}\n\n"
        f"Extracted context:\n{triage_result.get('extracted_context', '')}\n\n"
        f"Relevant Tools Docs:\n{combined_tool_docs}\n\n"
        f"Files list:\n{', '.join([json.dumps(item) if isinstance(item, dict) else str(item) for item in triage_result.get('files_list', [])])}\n\n"
        f"User prompt:\n{prompt}\n\n"
        f"{json_format_instructions}\n"
        "Please generate the complete .based file content."
    )

    # save generation prompt to file
    with open("generation_prompt.txt", "w") as f:
        f.write(generation_prompt)

    llm_conversation = [
        {"role": "system", "content": generation_prompt},
        {"role": "user", "content": f"Generate complete Based file content. Note that based resembles python, but instead of while true, based must use the loop until paradigm. SO you are generating BASED, NOT python code. Based *resembles* python but they are not the same. Be very careful with your generation. You must use the loop until functionality and paradigm. Otherwise, your agent will be incompatible with the engine and will FAIL.{USER_MESSAGE_BASED_GUIDELINES}"}
    ]

    # Attempt up to 5 times to validate
    max_attempts = 5
    attempt = 0
    generated_output = None
    final_output = None

    while attempt < max_attempts:
        try:
            generation_response = prompt_llm_json_output(
                conversation=llm_conversation,
                model=model,
                base_url=model_base_url,
                api_key=model_ak
            )

            print("\n\n\n\n\n\n\n\n\n")
            print("JSON Generation response:")
            print(generation_response)
            print("\n\n\n\n\n\n\n\n\n")
            
            content = generation_response.get("content")
            generated_output_obj = json.loads(content)
            
            print("\n\n\n\n\n\n\n\n\n")
            print("Generated output object:")
            print(generated_output_obj)
            print("\n\n\n\n\n\n\n\n\n")
            
            generated_output = generated_output_obj.get("text")
            new_file_name = generated_output_obj.get("filename")

            print("New file name", new_file_name)
            print("\n\n\n\n\n\n")
            print("New file content", generated_output)
            print("\n\n\n\n\n\n")

            
            if not generated_output:
                raise ValueError("Missing 'text' field in JSON response")
                
            validation_result = validate_based_code(generated_output)
            if validation_result.get("status") == "success":
                final_output = validation_result.get("converted_code", generated_output)
                print(f"Generated valid .based file: {final_output}")
                break
            else:
                error_msg = validation_result.get("error", "Unknown validation error")
                llm_conversation[0]["content"] += f"\nValidation error: {error_msg}"
                attempt += 1
                
        except (json.JSONDecodeError, ValueError) as e:
            # Handle JSON parsing error by retrying with updated prompt
            print(f"JSON parsing error (attempt {attempt+1}): {str(e)}")
            llm_conversation[0]["content"] += (
                f"\n\nYour previous response could not be parsed correctly. "
                f"Please ensure you return a valid JSON object exactly in this format: "
                f"{{\"type\": \"based\", \"filename\": \"example.based\", \"text\": \"your content here\"}}."
            )
            attempt += 1

    if final_output is None:
        return {
            "output": "Error: Unable to generate a valid Based file after multiple attempts.",
            "type": "response",
            "message": "Based file validation failed repeatedly."
        }

    return {
        "output": generated_output,
        "type": "based",
        "based_filename": new_file_name
    }


def _generate_based_diff(
    model: str,
    model_ak: str,
    model_base_url: str,
    selected_filename: str,
    prompt: str,
    selected_based_file: dict,
    triage_result: dict,
    relevant_tools: list
) -> dict:
    """
    Helper for handle_new_message: generate a diff to update an existing .based file.
    Uses a more flexible approach to diff validation.
    """
    print("\n\n\n\n\n\nSelected based file")
    print(selected_based_file)
    current_based_content = selected_based_file.get("latest_content", "")

    # This step aggregates the full documentation text for each relevant tool.
    relevant_docs = []
    for tool_name in relevant_tools:
        for t in TOOLS_DOCUMENTATION:
            if t["name"] == tool_name:
                # Use short description or the full 'docs' to pass along
                relevant_docs.append(f"Tool Name: {t['name']}\nFunction: {t['function']}\nDocs:\n{t['docs']}")
                break

    combined_tool_docs = "\n\n".join(relevant_docs)

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
        f"Relevant Tools:\n{combined_tool_docs}\n\n"
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
        try:
            generation_response = prompt_llm_json_output(
                conversation=llm_conversation,
                model=model,
                base_url=model_base_url,
                api_key=model_ak
            )
            print("\n\n\n\n\n\nGenerated Diff\n\n\n\n\n\n")
            
            content = generation_response.get("content")
            generated_diff_obj = json.loads(content)
            
            print("\n\n\n\n\n\n\n\n")
            print(generated_diff_obj)
            print("\n\n\n\n\n\n\n")
            
            generated_diff = generated_diff_obj.get("text")
            if not generated_diff:
                raise ValueError("Missing 'text' field in JSON response")
            
            print("\n\n\n\n\n\n\nSuccessfully parsed diff\n\n\n\n\n\n\n")
            
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
                
        except json.JSONDecodeError as e:
            # Handle JSON parsing error
            print(f"JSON parsing error (attempt {attempt+1}): {str(e)}")
            llm_conversation[0]["content"] += (
                f"\n\nYour previous response could not be parsed as JSON. "
                f"Please ensure you return a valid JSON object exactly in this format: "
                f"{{\"type\": \"diff\", \"filename\": \"file.based\", \"text\": \"--- file.based\\n+++ file.based\\n@@ -1,1 +1,2 @@\\n line1\\n+line2\"}}."
            )
            attempt += 1

    return {
        "output": "Error: Unable to generate a valid Based diff after multiple attempts.",
        "type": "response",
        "message": "Diff validation failed repeatedly."
    }


def tool_context_agent(
    prompt: str,
    triage_result: dict,
    conversation: list,
    tools_documentation: list,
    model: str,
    model_ak: str,
    model_base_url: str
) -> dict:
    """
    Decides which tools might be relevant to the user's request.
    Returns a dict like:
      {
        "tools": [
           "Gmail - Send Email",
           "Twilio - Send SMS"
        ]
      }
    or an empty "tools" list if none are relevant.
    """

    # Summarize the tool docs in a concise manner to the LLM
    # Or you can pass them in more detail if you prefer
    tools_summary = []
    for t in tools_documentation:
        tool_desc = f"{t['name']} - function: {t['function']}\nDescription: {t['shortDescription']}"
        tools_summary.append(tool_desc)
    tools_text = "\n\n".join(tools_summary)

    # Instruct the LLM to select relevant tools
    system_prompt = f"""
You are a "Tool Context Agent". The user prompt is:
{prompt}

We've already performed a high-level triage to gather context.
Here is the triage result:
{triage_result}

Here is the conversation so far:
{conversation}

Below is a list of available tools:

{tools_text}

Return a JSON object in the following format:
{{
   "tools": [ "Tool Name #1", "Tool Name #2", ...]
}}

Only include the names of the tools you deem relevant. If no tools are relevant, return an empty array.
"""

    llm_conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Which tools (by exact name) are relevant to the user's request?"}
    ]

    # Attempt to parse the JSON
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            generation_response = prompt_llm_json_output(
                conversation=llm_conversation,
                model=model,
                base_url=model_base_url,
                api_key=model_ak
            )
            content = generation_response.get("content", "{}")
            tool_json = json.loads(content)
            # Ensure we at least have a "tools" key
            if "tools" not in tool_json:
                raise ValueError("No 'tools' key found in the tool context agent response.")

            return tool_json

        except (json.JSONDecodeError, ValueError) as e:
            # If we fail to parse or "tools" key is missing, we prompt the LLM again
            llm_conversation[0]["content"] += (
                f"\n\nThe response could not be parsed. Make sure you return valid JSON with a 'tools' array. "
                f"Error detail: {str(e)}"
            )
            attempt += 1

    # If repeated failures, return empty
    return { "tools": [] }
