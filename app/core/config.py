# app/core/config.py
import PyPDF2
from io import BytesIO
import os

DATABASE_URL = "sqlite:///./my_database.db" 

VALIDATION_ENDPOINT = "https://brainbase-engine-python.onrender.com/validate"

BASED_GUIDE = """

```markdown
# Introduction – What is Brainbase?

**Brainbase** is the first-of-its-kind **Enterprise Agent Platform (EAP)** that provides large enterprise IT teams with a single place to **build**, **deploy**, and **test** their company’s AI workforce. Companies such as **Toyota** and **NBC** use Brainbase to build agents across **sales**, **marketing**, and **customer support**, and deploy them over **phone calls**, **SMS**, **email**, **chat**, and more. 

Our core technology is the **Based agent framework**, enabling enterprises to create **fully reliable, deterministic behavior** in their agents. This makes Brainbase feasible for **mission-critical**, customer-facing use cases in industries like **banking** and **healthcare**, where our competitors often fail to deliver due to reliability issues.

---

## What Is Based?

**Based** is a high-level AI instruction language designed to create **dynamic conversational agents** that operate flawlessly across multiple communication channels. It provides developers with an elegant, high-level syntax to build interactive workflows quickly and reliably.

### Key Features of Based

- **Intuitive and Expressive Syntax**  
  Develop complex conversational logic with clarity and brevity.

- **Specialized Constructs**  
  Utilize built-in keywords like `talk`, `loop`, `until`, and `ask` to manage conversation flow and state effortlessly.

- **Cross-Platform Flexibility**  
  Create agents deployable on **chat**, **voice**, **email**, **SMS**, and more—all while sharing data seamlessly across channels.
```

You are the world expert in writing in a language called Based that is designed for provisioning AI agents. It’s a high-level Pythonic language that has some additional syntax. It makes building agents easier.

**Loop-Until**

Based runs on the concept of conversational loops and handoffs. It splits an entire conversation flow into manageable chunks of conversation which hands off to other agents when certain conditions are met.

FORMAT:

```python
loop:
	res = talk("SYSTEM PROMPT FOR AGENT", True/False, {ANY INFO PASSED IN FROM PREVIOUS STEPS})
until "CONDITION 1":
	# OTHER AGENTS, CODE, ETC.
until "CONDITION 2":
	# OTHER AGENTS, CODE, ETC.
until ...
```

RULES:

- Rule 1: `loop`  can only have a single line in them and they have to be a `talk` line.
- Rule 2: each `until` can have return at the end of them that allows it to return information back to the `talk` loop, if there is not return in the `until` block after running that code it won’t return back to the `talk` loop again and will move on to the next loop

EXAMPLE: 

```python
loop:
	res = talk("Talk to the user about the weather and try to learn about their city and where they'd want to see the weather at.", True)
until "user mentions a city":
	# code for fetching the weather at the given city
	# weather = ...
	return weather # return it back to the talk loop to keep the conversation going
```

Here the AI will talk to the user until the user mentions a city, and then it will get information from an API or other integration to find out about the weather and return it back to the `talk` loop so that the AI can give that information back to the user. At the end of this, the user will be in the same loop again so they can mention another city and keep continuing.

BEST PRACTICES

- PRACTICE 1: In the `talk` calls, the system prompts should be of the format of system prompts that are detailed that explain
    - The agent’s purpose
    - The agent’s style of conversation
    - The exit (until) conditions
    - Example things that the user may say for it to exit into one of the untils
- PRACTICE 2: In the `talk` calls, pass in whatever information was obtained previously in the agent code that this agent should know as a dictionary in the `info` parameter
    
    This could include general information obtained before such as `{"name": <USER's NAME FROM PREVIOUS STEP>, "age": <USER AGE>}` as well as more detailed, use case specific ones such as `{"order_no": <ORDER NO>, "complaint_summary": <COMPLAINT SUMMARY>}`.
    
    Here, make sure that you’re passing in enough information for the agent to function well, but not too much that it will be inundated with unnecessary knowledge.
    

**Subagent**

One of the most powerful things you can do in Based is to call on subagents to perform one of AI tasks. You do this by calling the function `.ask` on any object defined in Based.

FORMAT:

```python
info = some_object_from_before.ask(
	question="The subagent's objective, in detail.",
	example={"name": "Brian Based", previous_jobs=["JOB 1", "JOB 2"]} # the exact return format as an example
)
```

RULES:

- Rule 1: `question` should clearly outline what is expected of this agent, some of the most common ones are:
    - Extract the `name` and `age` from this user output
    - Summarize what was said
    - Score the sentiment based on this criteria (detailed criteria here) from 1 (low) to 10 (high)
- Rule 2: each `until` can have return at the end of them that allows it to return information back to the `talk` loop, if there is not return in the `until` block after running that code it won’t return back to the `talk` loop again and will move on to the next loop

EXAMPLE:

```python
loop:
	res = talk("Talk to the user about the weather and try to learn about their city and where they'd want to see the weather at.", True)
until "user mentions a city":
	city_info = res.ask(question="Return the name of the city the user mentioned.", example={"city": "Boston"})
	# city_info now has {"city": "city user mentioned"} and can be used in
	# upcoming loops or API calls etc.
	# weather = ...
	return weather # return it back to the talk loop to keep the conversation going
```

BEST PRACTICES

- PRACTICE 1: Keep the `question` parameter in `.ask` as clear as possible
- PRACTICE 2: Make you `example` as detailed as possible, use reasonable fake example data on it to give the agent a better idea of what’s expected
- PRACTICE 3: Function calls in Based are done with a combination of loop-until and ask where the `until` decides what function is being called and `.ask` is then used to get the necessary parameters from the conversation that the until is coming from (see above example)

**API calls**

Based provides two primary built in functions for making `GET` and `POST` requests to external endpoints.

FORMAT

GET

```python
res = api.get_req(
	url="URL ENDPOINT TO CALL",
	params={"a": "...", "b": "..."}, # URL parameters to use
	headers={"Authentication": "..."} # headers to send
)

# res: {"response": {...}} # dictionary to return
```

POST

```python
res = api.post_req(
	url="URL ENDPOINT TO CALL",
	data={"a": "...", "b": "..."}, # data to send
	headers={"Authentication": "..."} # headers to send
)

# res: {"response": {...}} # dictionary to return
```

BEST PRACTICES

- PRACTICE 1: If you don’t know output schema of the api call, it’s a good idea to combine it with an ask to generate the schema you want out of it using a subagent
    
    EXAMPLE:
    
    ```python
    res = api.post_req(
    	url="URL ENDPOINT TO CALL",
    	data={"a": "...", "b": "..."}, # data to send
    	headers={"Authentication": "..."} # headers to send
    ) # unknown res schema
    info = res.ask(
    	question="Return the name and address info from this result.",
    	example={"name": "...", "address": "..."}
    ) # known schema as {"name": "...", "address": "..."}
    ```
    

Common patterns

Here are some common patterns of usage for Based.

Triage and handle

A common pattern in Based is to use nested loop-until structures for triaging user input and collecting necessary information. Here's an example:

```python
loop:
    res = talk("I am a customer service agent. I can help with orders, returns, or general questions. Please let me know what you need help with.", True)
until "user mentions order":
    loop:
        res = talk("What is your order number?", True)
    until "user provides order number":
        # Handle order-related query
        return handle_order({"order_no": "order number from conversation"})
until "user mentions return":
    loop:
        res = talk("What is the order number you want to return and what is the reason?", True)
    until "user provides return details":
        # Handle return request
        return process_return({"order_no": "order number from conversation", "reason": "reason from conversation"})
until "general question":
    # Handle general inquiries
    return handle_general_query(res)
```

This pattern is useful when you need to:

- Direct users to different handling paths based on their input
- Extract specific information before proceeding with specialized handling
- Maintain conversation context while switching between different handling modes

Sequential loop-untils

Another common pattern in Based is to use sequential loop-untils to gather information in a specific order. This is useful when you need to collect multiple pieces of information that build on each other. Here's an example:

```python
loop:
    res = talk("Hi! I'll help you set up your profile. First, what's your name?", True)
until "user provides name":
    name = res.ask(question="Extract the user's name", example={"name": "John Smith"})
    loop:
        res = talk(f"Nice to meet you {name['name']}! What's your age?", True, {"name": name['name']})
    until "user provides age":
        age = res.ask(question="Extract the user's age", example={"age": 25})
        loop:
            res = talk(f"Thanks! Finally, what's your preferred contact method?", True, 
                      {"name": name['name'], "age": age['age']})
        until "user provides contact method":
            contact = res.ask(question="Extract contact preference", 
                            example={"contact": "email"})
            return setup_profile(name, age, contact)
```

This pattern is particularly effective when:

- You need to collect information in a specific sequence
- Each piece of information depends on or builds upon previous responses
- You want to maintain a natural conversation flow while gathering data

The important thing to keep in mind here is not oversplitting a single simple prompt. In the above example for example you would be able to colllect name, age and preferred contact method in a single agent and have an until that said `user provided all three of name, age and contact number`


# Based Crash Course – Build Platform Agnostic Conversational Agents

## Introduction
Welcome to the **Based Crash Course**! This guide introduces you to **Based**, a powerful, domain-specific programming language designed to build platform agnostic conversational agents. Deploy conversational workflows on chat, voice, email, SMS, and more with ease, enabling seamless data exchange and a unified user experience across platforms.

---

## What Is Based?
**Based** is a high-level AI instruction language crafted to design dynamic conversational agents that operate flawlessly across multiple communication channels. It provides developers with an elegant, high-level syntax to build interactive workflows quickly and reliably.

### Key Features
- **Intuitive and Expressive Syntax**: Develop complex conversational logic with clarity and brevity.  
- **Specialized Constructs**: Utilize built-in keywords like `talk`, `loop`, `until`, and `ask` to manage conversation flow and state effortlessly.  
- **Cross-Platform Flexibility**: Create agents deployable on chat, voice, email, SMS, and more—all while sharing data seamlessly across channels.

---

## Core Conversation Flow Constructs
Based scripts use a trio of keywords to build interactive conversations:

1. **`talk`**: Sends a message or prompt to the user and waits for a response. (If you specify `False` as the second argument, it waits for the user to send a message first.)
2. **`loop`**: Begins a conversational block that allows for repeated prompting.
3. **`until`**: Specifies the condition under which the loop should end.

In practice, the `talk` keyword is typically enclosed in a `loop`/`until` structure. This pattern keeps the conversation repeating until valid input is obtained.

### Example Usage
```text
loop:
    # Send a prompt to the user asking for their preferred contact method.
    response = talk(
        "Hi there! What's your preferred contact method (email, phone, or SMS)?",
        True,
        {"preferred_contact": "email"} // Example default value
    )
until "User provides a valid contact method":
    contactInfo = response.ask(
        question="Extract and validate the contact method from the response.",
        example={"preferred_contact": "email"}
    )
    # Validate the contact method; if invalid, the prompt repeats.
    if contactInfo["preferred_contact"] not in ["email", "phone", "SMS"]:
        print("Invalid contact method provided. Re-prompting...")
    else:
        print("Valid contact method received!")

```markdown
# Based Language Fundamentals – Core Constructs Reference

Welcome to the **Based Language Fundamentals** guide. This reference document provides a comprehensive explanation of **Based**’s core language constructs, their declaration syntax, arguments, and practical usage examples. Understanding these fundamentals will enable you to build sophisticated conversational agents with precision and confidence.

---

## Core Language Constructs

Based is built around a set of specialized constructs designed specifically for conversational AI workflows. These constructs provide a high-level abstraction that makes it easy to build complex interactions without getting lost in implementation details.

---

## The `say` Function

The `say` function generates a response from the AI to the user **without** expecting a reply. It’s typically used to provide information, instructions, or acknowledgments.

**Syntax:**
```text
say(message, exact=False, model=None)
```

**Parameters**:
- **message (string)**: The content to be processed and presented to the user  
- **exact (boolean, optional)**: Controls how the message is processed  
  - **True**: Outputs exactly what’s provided in the message parameter, verbatim  
  - **False** (default): Allows the AI to rephrase the message while maintaining its meaning  
- **model (string, optional)**: Specifies which AI model to use for processing the message (when `exact=False`)

**Return Value**:
- Returns the response text, which can be stored in a variable for later use or simply executed for its side effect

**Example**:
```text
# Greet the user with an exact message
say("Welcome to BookBot! I'm here to help you find and reserve books.", exact=True)

# Generate a dynamic welcome based on intent
say("Generate a friendly welcome for a user looking for book recommendations")

# Store the response for later use
intro = say("Introduce yourself as a helpful assistant", model="anthropic/claude-3.7-sonnet")
```

---

## The `loop`, `talk`, and `until` Pattern

In Based, the `loop`, `talk`, and `until` constructs form an essential pattern that **must be used together**. This pattern creates interactive conversation flows that can repeat until specific conditions are met. The `talk` function is not meant to be used in isolation.

**Syntax:**
```text
loop:
    response = talk(
        system_prompt,
        first_prompt=True,
        default_values={},
        info={}
    )
until "Description of the completion condition":
    # Validation code that determines if the condition is met
    # The loop continues until this code completes successfully
```

### Parameters for `talk`:

- **system_prompt (string)**: Instruction or prompt that guides the conversation
- **first_prompt (boolean, optional)**: Controls conversation initiation  
  - **True** (default): AI starts by sending the prompt message to the user  
  - **False**: AI waits for the user to send a message first
- **default_values (dict, optional)**: Example values to structure expected responses
- **info (dict, optional)**: Additional context for the conversation

### The Loop-Until Pattern:

1. The **`loop`** keyword begins a repeatable conversation block  
2. The **`talk`** function within the loop handles the conversation exchange  
3. The **`until`** clause specifies a condition (in natural language) under which the loop should end  
4. The code block after **`until`** validates whether the condition has been met  
5. If the condition is met (the code executes successfully), the loop exits  
6. If the condition is not met, the loop repeats from the beginning

**Example**:
```text
loop:
    book_preference = talk(
        "What genre of books do you enjoy reading?",
        True,
        {"genre": "mystery", "format": "paperback"}
    )
until "User provides a valid book genre and format":
    preference_data = book_preference.ask(
        question="Extract the user's book genre and preferred format.",
        example={"genre": "mystery", "format": "paperback"}
    )

    # Validate the genre and format
    if preference_data["genre"] not in ["mystery", "sci-fi", "romance", "non-fiction"]:
        print("Invalid genre provided. Re-prompting...")
        continue

    if preference_data["format"] not in ["paperback", "hardcover", "e-book", "audiobook"]:
        print("Invalid format provided. Re-prompting...")
        continue

    # If we reach here, both genre and format are valid
    print("Valid preferences received!")
```

---

## Data Processing Methods

Based provides powerful methods to **transform and extract information** from data objects. These methods can be applied to any data object, not just conversation responses.

---

### The `.ask` Method

The `.ask` method extracts structured data from any data object, transforming unstructured content into well-formed data that can be used programmatically. This method can be used with API responses, conversation results, or any other data.

**Syntax:**
```text
data_object.ask(question, example=None, schema=None, model=None)
```

**Parameters**:
- **question (string)**: Instruction for extracting specific information from the data
- **example (dict, optional)**: Example object showing the expected output format
- **schema (dict, optional)**: JSON schema defining the expected structure
- **model (string, optional)**: AI model to use for extraction

**Return Value**:
- Returns structured data according to the example or schema provided

**Example**:
```text
# Extract structured book preferences from a conversation response
preferences = response.ask(
    question="Extract the user's preferred book genre, format, and any specific authors they mentioned.",
    example={
        "genre": "mystery",
        "format": "audiobook",
        "authors": ["Agatha Christie", "Arthur Conan Doyle"]
    }
)

# Use .ask on an API response
api_results = api.get_req(
    url='https://bookstore-api.example.com/books',
    headers={'authorization': 'Bearer ' + auth_token},
    params={'genre': 'mystery'}
).ask(
    question="Extract the book titles, authors, and prices from the API response.",
    example={"books": [{"title": "The Mystery", "author": "A. Writer", "price": "$12.99"}]}
)
```

---

### The `.summarize` Method

The `.summarize` method creates a concise summary of the information contained in any data object. This is particularly useful for **large text blocks or complex data structures**.

**Syntax:**
```text
data_object.summarize(prompt=None, model=None)
```

**Parameters**:
- **prompt (string, optional)**: Specific instruction for creating the summary
- **model (string, optional)**: AI model to use for summarization

**Return Value**:
- Returns a string containing the summary

**Example**:
```text
# Summarize a lengthy document
document_content = document.read(url="https://example.com/lengthy-report.pdf")
summary = document_content.summarize(
    prompt="Provide a 3-paragraph summary of this financial report, focusing on key metrics and projections."
)

# Create a concise summary of API results
search_results = google_search.search(query="latest developments in quantum computing")
key_points = search_results.summarize(
    prompt="Extract the 5 most significant recent breakthroughs in quantum computing mentioned in these results."
)
```

---

## Advanced Patterns

### Multiple `until` Statements

Based allows for sophisticated conversation flows by supporting **multiple `until` statements**. Each `until` block represents a different condition and can trigger different handling paths.

```text
# Multi-condition conversation handler example
loop:
    response = talk(
        "Welcome to our customer service bot. What can I help you with today?",
        True
    )
until "User wants to check order status":
    order_query = response.ask(
        question="Is the user asking about checking their order status? Extract order number if mentioned.",
        example={"is_order_status": true, "order_number": "ABC123"}
    )

    if order_query["is_order_status"]:
        # Handle order status request
        if "order_number" in order_query and order_query["order_number"]:
            order_details = get_order_details(order_query["order_number"])
            say(f"Your order {order_query['order_number']} is {order_details['status']}. Expected delivery: {order_details['delivery_date']}", exact=True)
        else:
            say("I'd be happy to check your order status. Could you please provide your order number?", exact=True)
        break
until "User wants to make a return":
    return_query = response.ask(
        question="Is the user asking about making a return? Extract product details if mentioned.",
        example={"is_return": true, "product": "Wireless Headphones"}
    )

    if return_query["is_return"]:
        # Handle return request
        say("I can help you process a return. Let me guide you through our return policy and steps.", exact=True)
        # Additional return handling logic
        break
until "User wants to speak to human agent":
    agent_query = response.ask(
        question="Does the user want to speak to a human agent?",
        example={"wants_human": true}
    )

    if agent_query["wants_human"]:
        say("I'll connect you with a customer service representative right away. Please hold for a moment.", exact=True)
        transfer_to_agent()
        break
```

---

### Conditional Flow Control

Based scripts can implement **conditional flow control** using standard Python syntax, allowing for dynamic conversation paths based on user responses.

```text
# Determine recommendation approach based on user expertise and preferences
loop:
    expertise_response = talk("How familiar are you with this book genre?", True)
until "User indicates their expertise level and reading preferences":
    user_profile = expertise_response.ask(
        question="Determine the user's expertise level and reading preferences.",
        example={
            "level": "beginner",
            "prefers_series": true,
            "likes_long_books": false
        }
    )

    # Create a personalized recommendation strategy
    if user_profile["level"] == "beginner":
        if user_profile["prefers_series"]:
            recommendations = get_beginner_series_recommendations(preferences["genre"])
            say(f"Since you're new to {preferences['genre']} and enjoy series, I recommend starting with these accessible series:", exact=True)
        else:
            recommendations = get_beginner_standalone_recommendations(preferences["genre"])
            say(f"For someone new to {preferences['genre']}, these standalone books are perfect introductions:", exact=True)
    elif user_profile["level"] == "intermediate":
        if user_profile["likes_long_books"]:
            recommendations = get_intermediate_long_recommendations(preferences["genre"])
        else:
            recommendations = get_intermediate_short_recommendations(preferences["genre"])
    else:
        # Expert reader
        recommendations = get_expert_recommendations(preferences["genre"])
        say(f"For an expert reader like yourself, these critically acclaimed {preferences['genre']} books offer complex narratives:", exact=True)

    # Display the recommendations
    for i, book in enumerate(recommendations[:3]):
        say(f"{i+1}. '{book['title']}' by {book['author']} - {book['description']}", exact=True)
```

---

## Platform-Specific Functions

Based supports different deployment platforms (**chat, voice, email, SMS**) and provides specialized functions for each platform. These functions allow you to take advantage of **platform-specific capabilities**.

---

### Voice Deployment Functions

When your Based agent is deployed for **voice conversations**, you can use these special functions to control call flow.

1. **`transfer_call(phone_number)`**: Transfers the current call to another phone number.
   ```text
   # Transfer call to customer support if user requests it
   if user_request["needs_human_support"]:
       say("I'll transfer you to our customer support team right away.", exact=True)
       transfer_call("+1-800-123-4567")
   ```

2. **`hangup()`**: Ends the current call.
   ```text
   # End call after completing the transaction
   say("Thank you for your order! Your confirmation number is ABC123. Have a great day!", exact=True)
   hangup()
   ```

---

### SMS Deployment Functions

For **SMS deployments**, Based provides specialized functions for text messaging.

- **`send_image(url)`**: Sends an image in the conversation.
  ```text
  # Send product image in SMS conversation
  product_details = get_product_info("ABC123")
  say(f"Here's the {product_details['name']} you inquired about:", exact=True)
  send_image(product_details["image_url"])
  ```

---

## Full Example: Book Recommendation Agent

Here’s a complete example that demonstrates the various language constructs working together, including **multiple `until` statements**:

```text
state = {}
meta_prompt = "You're a book recommendation assistant helping users find their next great read."
res = say("Hello! I'm BookBot, your personal book recommendation assistant.", exact=True)

# Introduce the service and set expectations
say("I can help you find books based on your preferences, including genre, format, and reading level.")

# Collect initial user preferences with multiple until paths
loop:
    initial_response = talk(
        f"{meta_prompt} Ask the user what they're looking for today, offering to recommend books, find new releases, or check book availability.",
        True
    )
until "User wants book recommendations":
    recommendation_request = initial_response.ask(
        question="Is the user asking for book recommendations?",
        example={"wants_recommendations": true}
    )

    if recommendation_request["wants_recommendations"]:
        # Handle recommendation path
        state["intent"] = "recommendations"

        # Collect genre preferences
        loop:
            genre_response = talk(
                "What genre of books do you enjoy reading?",
                True,
                {"genre": "fantasy", "format": "e-book"}
            )
        until "User provides valid genre and format preferences":
            preferences = genre_response.ask(
                question="Extract the user's preferred book genre and format.",
                example={"genre": "fantasy", "format": "e-book"}
            )

            if preferences["genre"] and preferences["format"]:
                state["preferences"] = preferences
                break

        # Generate recommendations
        recommendations = api.get_req(
            url='https://bookstore-api.example.com/recommendations',
            params=state["preferences"]
        ).ask(
            question="Extract the top 3 book recommendations with title, author, and description.",
            example={"books": [{"title": "Book Title", "author": "Author Name", "description": "Brief description"}]}
        )

        # Present recommendations
        say(f"Based on your interest in {state['preferences']['genre']} books, here are 3 titles I think you'll love:", exact=True)
        for i, book in enumerate(recommendations["books"]):
            say(f"{i+1}. '{book['title']}' by {book['author']}: {book['description']}", exact=True)
        break
until "User wants to check new releases":
    new_release_request = initial_response.ask(
        question="Is the user asking about new or upcoming book releases?",
        example={"wants_new_releases": true, "genre": "thriller"}
    )

    if new_release_request["wants_new_releases"]:
        # Handle new releases path
        state["intent"] = "new_releases"
        genre = new_release_request.get("genre", "")

        # Get new releases, optionally filtered by genre
        new_releases = api.get_req(
            url='https://bookstore-api.example.com/new-releases',
            params={"genre": genre} if genre else {}
        ).ask(
            question="Extract the latest 5 book releases with title, author, and release date.",
            example={"books": [{"title": "New Book", "author": "Author Name", "release_date": "2023-10-15"}]}
        )

        # Present new releases
        header = f"Here are the latest releases in {genre}:" if genre else "Here are the latest book releases:"
        say(header, exact=True)
        for i, book in enumerate(new_releases["books"]):
            say(f"{i+1}. '{book['title']}' by {book['author']} - Released: {book['release_date']}", exact=True)
        break
until "User wants to check book availability":
    availability_request = initial_response.ask(
        question="Is the user asking about checking if a specific book is available?",
        example={"checking_availability": true, "book_title": "The Great Novel", "author": "Famous Writer"}
    )

    if availability_request["checking_availability"]:
        # Handle availability check path
        state["intent"] = "check_availability"

        book_info = {}
        if "book_title" in availability_request:
            book_info["title"] = availability_request["book_title"]
        if "author" in availability_request:
            book_info["author"] = availability_request["author"]

        # If we have complete information, check availability
        if "title" in book_info and "author" in book_info:
            availability = check_book_availability(book_info["title"], book_info["author"])
            if availability["available"]:
                say(f"Good news! '{book_info['title']}' by {book_info['author']} is available in these formats: {', '.join(availability['formats'])}", exact=True)
            else:
                say(f"I'm sorry, '{book_info['title']}' by {book_info['author']} is currently unavailable. Would you like me to notify you when it becomes available?", exact=True)
        else:
            # Need more information
            loop:
                book_details_response = talk(
                    "I'd be happy to check book availability. Could you please provide the book title and author?",
                    True
                )
            until "User provides complete book details":
                details = book_details_response.ask(
                    question="Extract the book title and author from the user's response.",
                    example={"title": "The Great Novel", "author": "Famous Writer"}
                )

                if "title" in details and "author" in details:
                    availability = check_book_availability(details["title"], details["author"])
                    if availability["available"]:
                        say(f"Good news! '{details['title']}' by {details['author']} is available in these formats: {', '.join(availability['formats'])}", exact=True)
                    else:
                        say(f"I'm sorry, '{details['title']}' by {details['author']} is currently unavailable. Would you like me to notify you when it becomes available?", exact=True)
                    break
        break

# Conversation wrap-up
say("Is there anything else I can help you with today?", exact=True)
```

---

## Conclusion

The **Based language** provides a powerful yet intuitive framework for building conversational agents. By mastering the core constructs—particularly the essential **`loop-talk-until`** pattern—you can create sophisticated conversation flows that handle complex interactions while maintaining readability and maintainability.

Remember that **Based** is designed to be **declarative**, allowing you to focus on the *“what”* rather than the *“how”* of conversational AI. This approach dramatically reduces the amount of code needed to create powerful agents while increasing reliability and ease of maintenance.

The combination of the core language constructs with **platform-specific functions** allows you to build agents that take full advantage of each deployment platform’s unique capabilities while maintaining a consistent codebase and user experience. 
```

"""

UNIFIED_DIFF = """#!/usr/bin/env python
# coding=utf-8
# License: Public domain (CC0)
# Isaac Turner 2016/12/05

from __future__ import print_function

import difflib
import re

_no_eol = "\\ No newline at end of file"
_hdr_pat = re.compile("^@@ -(\\d+),?(\\d+)? \\+(\\d+),?(\\d+)? @@$")

def make_patch(a, b):
  \"\"\"
  Get unified string diff between two strings. Trims top two lines.
  Returns empty string if strings are identical.
  \"\"\"
  diffs = difflib.unified_diff(a.splitlines(True), b.splitlines(True), n=0)
  try:
    _, _ = next(diffs), next(diffs)
  except StopIteration:
    pass
  # diffs = list(diffs); print(diffs)
  return ''.join([d if d[-1] == '\\n' else d + '\\n' + _no_eol + '\\n' for d in diffs])

def apply_patch(s, patch, revert=False):
  \"\"\"
  Apply patch to string s to recover newer string.
  If revert is True, treat s as the newer string, recover older string.
  \"\"\"
  s = s.splitlines(True)
  p = patch.splitlines(True)
  t = ''
  i = sl = 0
  (midx, sign) = (1, '+') if not revert else (3, '-')
  while i < len(p) and p[i].startswith(("---", "+++")):
    i += 1  # skip header lines
  while i < len(p):
    m = _hdr_pat.match(p[i])
    if not m:
      raise Exception("Bad patch -- regex mismatch [line " + str(i) + "]")
    l = int(m.group(midx)) - 1 + (m.group(midx+1) == '0')
    if sl > l or l > len(s):
      raise Exception("Bad patch -- bad line num [line " + str(i) + "]")
    t += ''.join(s[sl:l])
    sl = l
    i += 1
    while i < len(p) and p[i][0] != '@':
      if i+1 < len(p) and p[i+1][0] == '\\\\':
        line = p[i][:-1]
        i += 2
      else:
        line = p[i]
        i += 1
      if len(line) > 0:
        if line[0] == sign or line[0] == ' ':
          t += line[1:]
        sl += (line[0] != sign)
  t += ''.join(s[sl:])
  return t

#
# Testing
#

import random
import string
import traceback
import sys
import codecs

def test_diff(a, b):
  mp = make_patch(a, b)
  try:
    assert apply_patch(a, mp) == b
    assert apply_patch(b, mp, True) == a
  except Exception as e:
    print("=== a ===")
    print([a])
    print("=== b ===")
    print([b])
    print("=== mp ===")
    print([mp])
    print("=== a->b ===")
    print(apply_patch(a, mp))
    print("=== a<-b ===")
    print(apply_patch(b, mp, True))
    traceback.print_exc()
    sys.exit(-1)

def randomly_interleave(*args):
  \"\"\" Randomly interleave multiple lists/iterators \"\"\"
  iters = [iter(x) for x in args]
  while iters:
    i = random.randrange(len(iters))
    try:
      yield next(iters[i])
    except StopIteration:
      # swap empty iterator to end and remove
      iters[i], iters[-1] = iters[-1], iters[i]
      iters.pop()

def rand_ascii():
  return random.choice(string.printable)

def rand_unicode():
  a = u"\\u%04x" % random.randrange(0x10000)
  # return a.decode('utf-8')
  return str(codecs.encode(a, 'utf-8'))

def generate_test(nlines=10, linelen=10, randchar=rand_ascii):
  \"\"\"
  Generate two strings with approx `nlines` lines, which share approx half their
  lines. Then run the diff/patch test unit with the two strings.
  Lines are random characters and may include newline / linefeeds.
  \"\"\"
  aonly, bonly, nshared = (random.randrange(nlines) for _ in range(3))
  a = [''.join([randchar() for _ in range(linelen)]) for _ in range(aonly)]
  b = [''.join([randchar() for _ in range(linelen)]) for _ in range(bonly)]
  ab = [''.join([randchar() for _ in range(linelen)]) for _ in range(nshared)]
  a = list(randomly_interleave(a, ab))
  b = list(randomly_interleave(b, ab))
  test_diff(''.join(a), ''.join(b))

def std_tests():
  test_diff("asdf\nhamster\nmole\nwolf\ndog\ngiraffe",
            "asdf\nhampster\nmole\nwolf\ndooog\ngiraffe\n")
  test_diff("asdf\nhamster\nmole\nwolf\ngiraffe",
            "hampster\nmole\nwolf\ndooog\ngiraffe\n")
  test_diff("hamster\nmole\nwolf\ndog",
            "asdf\nhampster\nmole\nwolf\ndooog\ngiraffe\n")
  test_diff("", "")
  test_diff("", "asdf\nasf")
  test_diff("asdf\nasf", "xxx")
  # Things can get nasty, we need to be able to handle any input
  # see https://docs.python.org/3/library/stdtypes.html
  test_diff("\\x0c", "\\n\\r\\n")
  test_diff("\\x1c\\v", "\\f\\r\\n")

def main():
  print("Testing...")
  std_tests()
  print("Testing random ASCII...")
  for _ in range(50):
    generate_test(50, 50, rand_ascii)
  print("Testing random unicode...")
  for _ in range(50):
    generate_test(50, 50, rand_unicode)
  print("Passed ✓")

if __name__ == '__main__':
  main()
"""

VALIDATION_FUNCTION = """def validate_based_diff(diff: str, current_content: str) -> dict:
    \"\"\"
    Validate a generated Based diff by first verifying it locally using unifieddiff,
    then validating the updated content via an external validation endpoint.

    Steps:
      1. Apply the provided diff to the current content.
      2. Recompute the diff between the original and updated content.
      3. If the recomputed diff does not match the provided diff (after stripping whitespace),
         return an error.
      4. If the diff passes the local test, send the updated content to the validation endpoint.
      
    Returns:
      On success: {"status": "success", "converted_diff": <diff>, "updated_content": <new_content>}
      On failure: {"status": "error", "error": <error message>}
    \"\"\"
    try:
        # Apply the diff locally.
        new_content = unifieddiff.apply_patch(current_content, diff)
        print("=== Local diff test passed ===")
        print("new_content:", new_content)
        recomputed_diff = unifieddiff.make_patch(current_content, new_content)
        if recomputed_diff.strip() != diff.strip():
            print("=== Local diff test failed ===")
            return {"status": "error", "error": "Local diff test failed: inconsistent diff."}
    except Exception as e:
        print("=== Local diff test exception ===")
        return {"status": "error", "error": f"Local diff test exception: {str(e)}"}

    # Validate the updated content via external endpoint.
    payload = {"code": new_content}
    print("=== validate_based_diff ===")
    print(payload)
    try:
        r = requests.post(VALIDATION_ENDPOINT, json=payload, timeout=10)
        result = r.json()
        # On success, attach updated content to the return object.
        if result.get("status") == "success":
            result["updated_content"] = new_content
        return result
    except Exception as e:
        return {"status": "error", "error": f"External validation error: {str(e)}"}
"""

USER_MESSAGE_BASED_GUIDELINES = """
To ensure that conversation flows adhere strictly to our guidelines, the system prompt must now enforce the use of the loop until syntax for controlling dialogue transitions. Every conversational cycle must consist of a single 'talk' call, immediately followed by a corresponding 'until' block that evaluates exit conditions and transitions to the next state. You are allowed multiple until blocks but only one loop.For example:

loop until (the response matches the expected intent) {
    talk("Hello, thank you for calling. How may I assist you today?");
    // Evaluate the user’s reply and, if it meets the required condition, proceed; otherwise, remain in the loop until it does.
}

This structure clearly separates the moment of interaction (the talk call) from exit and transition checks in the 'until' block. The agent’s purpose is to ensure clarity in conversation, where each loop precisely handles one part of the interaction, and any subsequent action or state change is determined exclusively by the corresponding 'until' clause. The conversation style should always remain friendly and instructional, guiding the user through step-by-step queries until a complete response is received.

Agents must document each loop with comments that explain the intended transition. For instance, when waiting for confirmation of user details, the 'until' construct should explicitly define that the loop only terminates when the user confirms the details. This consistent use of the loop until syntax combats any drift towards traditional while loops, thereby enforcing a well-structured, repeatable, and transparent conversation flow. Deviations from this pattern should be immediately corrected to align with our mandated design principles.
"""

TOOLS_DOCUMENTATION = [
    # Gmail
    {
        "name": "Gmail - Send Email",
        "shortDescription": "Send an email through a Gmail account",
        "function": "gmail.send_email",
        "docs": """Sends an email through a Gmail account.
    
Input:
- receiver (Required): Email address of the receiver, or multiple addresses separated by commas
- subject (Required): The email subject
- body_text (Required): Text version of the body for the email you want to send
- reply_to (Optional): Email address to set as the "Reply-To" header
- body_html (Optional): HTML version of the body for the email you want to send
- attachment (Optional): File to attach to the email you want to send

Example: 
gmail.send_email({
  receiver: "example@example.com",
  subject: "Meeting Reminder",
  body_text: "Don't forget our meeting tomorrow at 2pm."
})"""
    },
    {
        "name": "Gmail - Find Email",
        "shortDescription": "Find an email in your Gmail account",
        "function": "gmail.gmail_search_mail",
        "docs": """Searches for an email in your Gmail account.
    
Input:
- subject (Optional): The email subject
- fromAddress (Optional): The address sending the new mail
- to (Optional): The address receiving the new mail
- label (Optional): The label tagged to the mail
- category (Optional): Category of the mail

Example:
gmail.gmail_search_mail({
  subject: "Invoice",
  fromAddress: "billing@company.com"
})"""
    },

    # Google Sheets
    {
        "name": "Google Sheets - Insert Row",
        "shortDescription": "Append a row of values to an existing sheet",
        "function": "google_sheets.insert_row",
        "docs": """Append a row of values to an existing sheet.
    
Input:
- spreadsheet_id (Required): The spreadsheet's unique identifier
- include_team_drives (Required): Determines if sheets from Team Drives should be included
- sheet_id (Required): The sheet's unique identifier
- as_string (Optional): Inserted values that are dates and formulas will be entered as strings
- first_row_headers (Required): If the first row is headers
- values (Required): The values to insert

Example:
google_sheets.insert_row({
  spreadsheet_id: "1abc123def456",
  include_team_drives: true,
  sheet_id: "Sheet1",
  first_row_headers: true,
  values: { name: "John Doe", email: "john@example.com" }
})"""
    },
    {
        "name": "Google Sheets - Delete Row",
        "shortDescription": "Delete a row on an existing sheet",
        "function": "google_sheets.delete_row",
        "docs": """Delete a row on an existing sheet you have access to.
    
Input:
- spreadsheet_id (Required): The spreadsheet's unique identifier
- include_team_drives (Required): Determines if sheets from Team Drives should be included
- sheet_id (Required): The sheet's unique identifier
- row_id (Required): The row number to remove

Example:
google_sheets.delete_row({
  spreadsheet_id: "1abc123def456",
  include_team_drives: true,
  sheet_id: "Sheet1",
  row_id: 4
})"""
    },
    {
        "name": "Google Sheets - Update Row",
        "shortDescription": "Overwrite values in an existing row",
        "function": "google_sheets.update_row",
        "docs": """Overwrite values in an existing row.
    
Input:
- spreadsheet_id (Required): The spreadsheet's unique identifier
- include_team_drives (Required): Determines if sheets from Team Drives should be included
- sheet_id (Required): The sheet's unique identifier
- row_id (Required): The row number to update
- first_row_headers (Required): If the first row is headers
- values (Required): The values to insert

Example:
google_sheets.update_row({
  spreadsheet_id: "1abc123def456",
  include_team_drives: true,
  sheet_id: "Sheet1",
  row_id: 5,
  first_row_headers: true,
  values: { name: "Jane Doe", email: "jane@example.com" }
})"""
    },
    {
        "name": "Google Sheets - Find Rows",
        "shortDescription": "Find rows in a Google Sheet",
        "function": "google_sheets.find_rows",
        "docs": """Find rows in a Google Sheet.
    
Input:
- spreadsheet_id (Required): The spreadsheet's unique identifier
- include_team_drives (Required): Determines if sheets from Team Drives should be included
- sheet_id (Required): The sheet's unique identifier
- column_name (Required): Column Name
- search_value (Required): The value to search for

Example:
google_sheets.find_rows({
  spreadsheet_id: "1abc123def456",
  include_team_drives: true,
  sheet_id: "Sheet1",
  column_name: "email",
  search_value: "jane@example.com"
})"""
    },
    {
        "name": "Google Sheets - Clear Sheet",
        "shortDescription": "Clears all rows on an existing sheet",
        "function": "google_sheets.clear_sheet",
        "docs": """Clears all rows on an existing sheet.
    
Input:
- spreadsheet_id (Required): The spreadsheet's unique identifier
- include_team_drives (Required): Determines if sheets from Team Drives should be included
- sheet_id (Required): The sheet's unique identifier
- is_first_row_headers (Required): If the first row is headers

Example:
google_sheets.clear_sheet({
  spreadsheet_id: "1abc123def456",
  include_team_drives: true,
  sheet_id: "Sheet1",
  is_first_row_headers: true
})"""
    },

    # Google Calendar
    {
        "name": "Google Calendar - Update Event",
        "shortDescription": "Updates an event in Google Calendar",
        "function": "google_calendar.update_event",
        "docs": """Updates an event in Google Calendar.
    
Input:
- calendar_id (Required): The calendar's identifier
- eventId (Required): The event's identifier
- title (Optional): The event title
- start_date_time (Optional): The start date and time
- end_date_time (Optional): The end date and time
- summary (Optional): The event summary

Example:
google_calendar.update_event({
  calendar_id: "primary",
  eventId: "abc123def456",
  title: "Team Meeting",
  start_date_time: "2023-06-15T10:00:00",
  end_date_time: "2023-06-15T11:00:00"
})"""
    },

    # Google Contacts
    {
        "name": "Google Contacts - Add Contact",
        "shortDescription": "Add a contact to a Google Contacts account",
        "function": "google_contacts.add_contact",
        "docs": """Add a contact to a Google Contacts account.
    
Input:
- firstName (Required): The first name of the contact
- middleName (Optional): The middle name of the contact
- lastName (Required): The last name of the contact
- jobTitle (Optional): The job title of the contact
- company (Optional): The company of the contact
- email (Optional): The email address of the contact
- phoneNumber (Optional): The phone number of the contact

Example:
google_contacts.add_contact({
  firstName: "John",
  lastName: "Smith",
  email: "john.smith@example.com",
  phoneNumber: "+1234567890",
  jobTitle: "Software Engineer",
  company: "Tech Corp"
})"""
    },

    # Slack
    {
        "name": "Slack - Send Message To A User",
        "shortDescription": "Send message to a user on Slack",
        "function": "slack.send_direct_message",
        "docs": """Send message to a user on Slack.
    
Input:
- userId (Required): Message receiver
- text (Required): The text of your message
- username (Optional): The username of the bot
- profilePicture (Optional): The profile picture of the bot

Example:
slack.send_direct_message({
  userId: "U012ABC3456",
  text: "Hello, could you review the document I shared?",
  username: "Notification Bot"
})"""
    },
    {
        "name": "Slack - Send Message To A Channel",
        "shortDescription": "Send message to a channel on Slack",
        "function": "slack.send_channel_message",
        "docs": """Send message to a channel on Slack.
    
Input:
- channel (Required): Channel, private group, or IM channel to send message to
- text (Required): The text of your message
- username (Optional): The username of the bot
- profilePicture (Optional): The profile picture of the bot

Example:
slack.send_channel_message({
  channel: "C012ABC3456",
  text: "The weekly report is now available!",
  username: "Report Bot"
})"""
    },
    {
        "name": "Slack - Request Approval From A User",
        "shortDescription": "Send approval message to a user and wait for response",
        "function": "slack.request_approval_direct_message",
        "docs": """Send approval message to a user and then wait until the message is approved or disapproved.
    
Input:
- userId (Required): Message receiver
- text (Required): The text of your message
- username (Optional): The username of the bot
- profilePicture (Optional): The profile picture of the bot

Example:
slack.request_approval_direct_message({
  userId: "U012ABC3456",
  text: "Can you approve the purchase order #12345?",
  username: "Approval Bot"
})"""
    },
    {
        "name": "Slack - Request Approval in a Channel",
        "shortDescription": "Send approval message to a channel and wait for response",
        "function": "slack.request_approval_message",
        "docs": """Send approval message to a channel and then wait until the message is approved or disapproved.
    
Input:
- channel (Required): Channel, private group, or IM channel to send message to
- text (Required): The text of your message
- username (Optional): The username of the bot
- profilePicture (Optional): The profile picture of the bot

Example:
slack.request_approval_message({
  channel: "C012ABC3456",
  text: "Team, can someone approve the new design mockups?",
  username: "Design Approval Bot"
})"""
    },

    # Salesforce
    {
        "name": "Salesforce - Run Query",
        "shortDescription": "Run a Salesforce query",
        "function": "salesforce.run_query",
        "docs": """Run a Salesforce query.
    
Input:
- query (Required): Enter the SOQL query

Example:
salesforce.run_query({
  query: "SELECT Id, Name FROM Account WHERE LastModifiedDate > YESTERDAY"
})"""
    },
    {
        "name": "Salesforce - Create Object",
        "shortDescription": "Create a new object in Salesforce",
        "function": "salesforce.create_new_object",
        "docs": """Create a new object in Salesforce.
    
Input:
- object (Required): Select the Object
- data (Required): Select mapped object

Example:
salesforce.create_new_object({
  object: "Lead",
  data: {
    FirstName: "John",
    LastName: "Smith",
    Email: "john.smith@example.com",
    Company: "ABC Corp"
  }
})"""
    },
    {
        "name": "Salesforce - Update Object",
        "shortDescription": "Update an existing object in Salesforce",
        "function": "salesforce.update_object_by_id",
        "docs": """Update an object by Id in Salesforce.
    
Input:
- object (Required): Select the Object
- id (Required): Select the Id
- data (Required): Select mapped object

Example:
salesforce.update_object_by_id({
  object: "Contact",
  id: "003XXXXXXXXXXXXXXX",
  data: {
    Phone: "+1234567890",
    Title: "CTO"
  }
})"""
    },
    {
        "name": "Salesforce - Batch Upsert",
        "shortDescription": "Batch upsert records by external id",
        "function": "salesforce.upsert_by_external_id",
        "docs": """Batch upsert records by external id in Salesforce.
    
Input:
- object (Required): Select the Object
- external_field (Required): Select the External Field
- records (Required): Select the Records

Example:
salesforce.upsert_by_external_id({
  object: "Account",
  external_field: "External_ID__c",
  records: [
    {
      External_ID__c: "A001",
      Name: "Acme Corp",
      Industry: "Technology"
    },
    {
      External_ID__c: "A002", 
      Name: "Globex",
      Industry: "Manufacturing"
    }
  ]
})"""
    },

    # Monday
    {
        "name": "Monday - Create Item",
        "shortDescription": "Create a new item inside a board",
        "function": "monday.monday_create_item",
        "docs": """Create a new item inside a board on Monday.com.
    
Input:
- workspace_id (Required): The workspace's unique identifier
- board_id (Required): The board's unique identifier
- group_id (Optional): Board Group
- item_name (Required): Item Name
- column_values (Optional): The column values of the new item
- create_labels_if_missing (Optional): Creates status/dropdown labels if they are missing

Example:
monday.monday_create_item({
  workspace_id: "12345",
  board_id: "67890",
  group_id: "topics",
  item_name: "New Feature Implementation",
  column_values: {
    status: "Working on it",
    date: "2023-06-30",
    person: "12345"
  },
  create_labels_if_missing: true
})"""
    },

    # LinkedIn
    {
        "name": "LinkedIn - Search People",
        "shortDescription": "Search for people on LinkedIn",
        "function": "linkedin.search_people",
        "docs": """Search for people on LinkedIn.
    
Input:
- keywords (Optional): Keywords to search for
- keywordsFirstName (Optional): Keywords to search for in first name
- keywordsLastName (Optional): Keywords to search for in last name
- keywordsTitle (Optional): Keywords to search for in title
- keywordsCompany (Optional): Keywords to search for in company
- keywordsSchool (Optional): Keywords to search for in school
- networkDepths (Optional): Depth of connection
- limit (Optional): Limit number of results

Example:
linkedin.search_people({
  keywordsTitle: "Software Engineer",
  keywordsCompany: "Google",
  limit: 10
})"""
    },
    {
        "name": "LinkedIn - Get Own Profile",
        "shortDescription": "Retrieve your own LinkedIn profile",
        "function": "linkedin.get_own_profile",
        "docs": """Get your own LinkedIn profile information.
    
Input: No parameters required

Example:
linkedin.get_own_profile()"""
    },
    {
        "name": "LinkedIn - Send Invite",
        "shortDescription": "Send an invitation to a LinkedIn user",
        "function": "linkedin.send_invite",
        "docs": """Send an invite to a LinkedIn user.
    
Input:
- profileId (Required): The profile ID of the user
- message (Optional): The message to send to the user

Example:
linkedin.send_invite({
  profileId: "john-smith-12345",
  message: "I'd like to connect with you to discuss potential collaboration opportunities."
})"""
    },

    # Outlook
    {
        "name": "Outlook - Send Email",
        "shortDescription": "Send an email using Outlook",
        "function": "outlook.send_email",
        "docs": """Send an email using Microsoft Outlook.
    
Input:
- fromAddress (Optional): The sender's email address
- to (Required): Recipient email addresses
- cc (Optional): CC recipient email addresses
- replyTo (Optional): Reply-to email address
- bcc (Optional): BCC recipient email addresses
- subject (Required): Email subject
- body (Required): Email body content

Example:
outlook.send_email({
  to: ["recipient@example.com"],
  subject: "Meeting Agenda",
  body: "Here's the agenda for our upcoming meeting...",
  cc: ["manager@example.com"]
})"""
    },

    # Twilio
    {
        "name": "Twilio - Send SMS",
        "shortDescription": "Send an SMS message using Twilio",
        "function": "twilio.send_sms",
        "docs": """Send a new SMS message using Twilio.
    
Input:
- fromNumber (Required): The phone number to send the message from
- body (Required): The body of the message to send
- toNumber (Required): The phone number to send the message to

Example:
twilio.send_sms({
  fromNumber: "+12345678901",
  toNumber: "+19876543210",
  body: "Your appointment is confirmed for tomorrow at 2pm."
})"""
    },

    # Voice
    {
        "name": "Voice - Make Phone Call",
        "shortDescription": "Make a phone call to a number",
        "function": "voice.call",
        "docs": """Make a phone call to a phone number.
    
Input:
- fromNumber (Required): The phone number to call from
- toNumber (Required): The phone number to call
- info (Required): The information to use for the call
- objective (Required): The objective of the call
- start_sentence (Optional): The start sentence of the call
- voiceId (Optional): The voice ID to use for the call
- language (Optional): The language to use for the call
- callId (Optional): The ID of the caller
- model (Optional): The model to use for the request (default: gpt-3.5-turbo-16k)
- wsBaseUrl (Optional): The base URL for the websocket

Example:
voice.call({
  fromNumber: "+12345678901",
  toNumber: "+19876543210",
  info: { name: "John Smith", appointment_time: "2pm tomorrow" },
  objective: "Confirm the customer's appointment",
  start_sentence: "Hello, I'm calling from ABC Clinic to confirm your appointment.",
  voiceId: "Alloy"
})"""
    },

    # File
    {
        "name": "File - Save File",
        "shortDescription": "Save a file to the file system",
        "function": "file.save_file",
        "docs": """Save a file to the file system.
    
Input:
- name (Required): The name of the file to save
- content (Required): The content of the file to save
- extension (Required): The extension of the file to save

Example:
file.save_file({
  name: "customer_data",
  content: "Name,Email,Phone\\nJohn Doe,john@example.com,123-456-7890",
  extension: "csv"
})"""
    },

    # Extract
    {
        "name": "Extract - Extract Information",
        "shortDescription": "Extract structured information from text",
        "function": "extract.extract",
        "docs": """Extract information from text.
    
Input:
- text (Required): The text from which the information needs to be extracted
- titles (Required): Titles for the information to be extracted, separated by commas
- descriptions (Required): Descriptions for the information to be extracted, separated by commas
- enums (Required): Enums for the information to be extracted, separated by commas
- temperature (Optional): The temperature of the model (0-1)
- model (Optional): The model to use (default: gpt-3.5-turbo-16k)

Example:
extract.extract({
  text: "John Doe has 5 years of experience working at Google as a software engineer.",
  titles: "Name, Experience, Company, Position",
  descriptions: "The name of the person, Years of work experience, Company name, Job title",
  enums: "1, 2, 3, 4, 5, 6, 7, 8, 9, 10"
})"""
    },

    # Answer
    {
        "name": "Answer - Answer Question",
        "shortDescription": "Answer a question based on provided information",
        "function": "answer.answer",
        "docs": """Answer a question based on provided information.
    
Input:
- obj (Required): The object to extract information from
- question (Required): The question to answer
- model (Optional): The model to use (default: gpt-3.5-turbo-16k)

Example:
answer.answer({
  obj: { name: "John", age: 30, occupation: "Software Engineer" },
  question: "What is John's occupation?"
})"""
    },

    # Link
    {
        "name": "Link - Read Text From Link",
        "shortDescription": "Read text content from a URL",
        "function": "link.read_link",
        "docs": """Read the text content from a link.
    
Input:
- link (Required): The URL to read the text from

Example:
link.read_link({
  link: "https://example.com/article"
})"""
    },
    {
        "name": "Link - Read Text From Link Using Vision",
        "shortDescription": "Read text content from a URL using vision capabilities",
        "function": "link.read_link_vision",
        "docs": """Read text content from a link using vision capabilities.
    
Input:
- link (Required): The URL to read the text from
- schema (Required): The schema to use for the request

Example:
link.read_link_vision({
  link: "https://example.com/infographic",
  schema: "title, main_points, key_takeaways"
})"""
    },

    # Brainbase Table
    {
        "name": "Brainbase Table - Find Rows",
        "shortDescription": "Read rows from a database table",
        "function": "brainbase_table.find_rows",
        "docs": """Read rows from a table in the database.
    
Input:
- timezone (Optional): Timezone for the mysql server to use
- table (Required): The name of the table
- condition (Required): SQL condition, can also include logic operators
- args (Optional): Arguments can be used using ? in the condition
- columns (Optional): Specify the columns you want to select

Example:
brainbase_table.find_rows({
  table: "customers",
  condition: "last_purchase_date > ? AND status = ?",
  args: ["2023-01-01", "active"],
  columns: ["id", "name", "email"]
})"""
    },
    {
        "name": "Brainbase Table - Insert Row",
        "shortDescription": "Insert a new row into a database table",
        "function": "brainbase_table.insert_row",
        "docs": """Insert a new row into a table.
    
Input:
- timezone (Optional): Timezone for the mysql server to use
- table (Required): The name of the table
- values (Required): Values to be inserted into the row

Example:
brainbase_table.insert_row({
  table: "customers",
  values: {
    name: "John Doe",
    email: "john@example.com",
    status: "active",
    signup_date: "2023-05-15"
  }
})"""
    },
    {
        "name": "Brainbase Table - Update Row",
        "shortDescription": "Update row(s) in a database table",
        "function": "brainbase_table.update_row",
        "docs": """Update one or more rows in a table.
    
Input:
- timezone (Optional): Timezone for the mysql server to use
- table (Required): The name of the table
- values (Required): Values to be updated
- search_column (Required): Column to search on
- search_value (Required): Value to search for

Example:
brainbase_table.update_row({
  table: "customers",
  values: {
    status: "inactive",
    last_updated: "2023-06-01"
  },
  search_column: "email",
  search_value: "john@example.com"
})"""
    },
    {
        "name": "Brainbase Table - Delete Row",
        "shortDescription": "Delete row(s) from a database table",
        "function": "brainbase_table.delete_row",
        "docs": """Delete one or more rows from a table.
    
Input:
- timezone (Optional): Timezone for the mysql server to use
- table (Required): The name of the table
- search_column (Required): Column to search on
- search_value (Required): Value to search for

Example:
brainbase_table.delete_row({
  table: "customers",
  search_column: "status",
  search_value: "inactive"
})"""
    },
    {
        "name": "Brainbase Table - Get Tables",
        "shortDescription": "Get a list of tables in the database",
        "function": "brainbase_table.get_tables",
        "docs": """Returns a list of tables in the database.
    
Input: No parameters required

Example:
brainbase_table.get_tables()"""
    },
    {
        "name": "Brainbase Table - Execute Query",
        "shortDescription": "Execute a custom SQL query",
        "function": "brainbase_table.execute_query",
        "docs": """Execute a custom SQL query on the database.
    
Input:
- timezone (Optional): Timezone for the mysql server to use
- query (Required): The query string to execute, use ? for arguments
- args (Optional): Can be inserted in the query string using ?

Example:
brainbase_table.execute_query({
  query: "SELECT * FROM customers WHERE signup_date BETWEEN ? AND ? ORDER BY name",
  args: ["2023-01-01", "2023-06-30"]
})"""
    },

    # Google Search
    {
        "name": "Google Search - Search",
        "shortDescription": "Search for information on Google",
        "function": "google_search.search",
        "docs": """Search for the top results on Google given the query.
    
Input:
- query (Required): The query to search for on Google
- type (Optional): The type of search to perform

Example:
google_search.search({
  query: "latest developments in artificial intelligence",
  type: "news"
})"""
    },

    # Code
    {
        "name": "Code - Run Code",
        "shortDescription": "Execute code",
        "function": "code.run",
        "docs": """Run code with specified variables.
    
Input:
- globalVariables (Required): The dictionary of all variables
- code (Required): The code to be executed

Example:
code.run({
  globalVariables: {
    name: "John",
    age: 30,
    items: ["apple", "banana", "orange"]
  },
  code: "const message = 'Hello ' + name + '! You are ' + age + ' years old.'; return message;"
})"""
    },

    # Brainbase Forms
    {
        "name": "Brainbase Forms - Fill In",
        "shortDescription": "Fill in a form with data",
        "function": "brainbase_forms.fill_in",
        "docs": """Fill in a form with data.
    
Input:
- data (Required): The data to be filled in the form
- formTemplateId (Required): The ID of the Brainbase form template
- fontSize (Optional): The font size for the text

Example:
brainbase_forms.fill_in({
  formTemplateId: "form-123",
  data: {
    name: "John Doe",
    address: "123 Main St, Anytown, USA",
    phone: "555-123-4567"
  },
  fontSize: 12
})"""
    },

    # API
    {
        "name": "API - GET Request",
        "shortDescription": "Make a GET request to an API endpoint",
        "function": "api.get_req",
        "docs": """Send a GET request to an API endpoint.
    
Input:
- url (Required): The URL of the API endpoint
- params (Optional): The query parameters to include in the request
- headers (Optional): The headers to include in the request

Example:
api.get_req({
  url: "https://api.example.com/users",
  params: {
    page: 1,
    limit: 10
  },
  headers: {
    "Authorization": "Bearer token123"
  }
})"""
    },
    {
        "name": "API - POST Request",
        "shortDescription": "Make a POST request to an API endpoint",
        "function": "api.post_req",
        "docs": """Send a POST request to an API endpoint.
    
Input:
- url (Required): The URL of the API endpoint
- data (Required): The JSON data to send in the request
- headers (Optional): The headers to include in the request

Example:
api.post_req({
  url: "https://api.example.com/users",
  data: {
    name: "John Doe",
    email: "john@example.com"
  },
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer token123"
  }
})"""
    }
]

def detect_file_type(ext: str) -> str:
    # Basic classification by extension
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
        return "image"
    elif ext == ".pdf":
        return "pdf"
    elif ext == ".csv":
        return "csv"
    elif ext in [".md", ".markdown"]:
        return "markdown"
    elif ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".rb", ".go", ".rs"]:
        return "code"
    elif ext in [".exe", ".bin", ".dll"]:
        return "computer"
    else:
        return "other"
    


def parse_file_content(file_path: str, file_type: str) -> str:
    """
    Read and parse file content from disk for code/csv/markdown/pdf.
    For images or 'other', we return empty content.
    """
    if not os.path.exists(file_path):
        return ""

    if file_type in ["code", "csv", "markdown", "based"]:
        # Read as text
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except:
            return ""

    elif file_type == "pdf":
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                pdf_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pdf_text += text
            return pdf_text
        except:
            return "[Error parsing PDF]"

    # If image, 'computer', or other, we don't parse text
    return ""
