# app/core/config.py

DATABASE_URL = "sqlite:///./my_database.db" 

VALIDATION_ENDPOINT = "https://brainbase-engine-python.onrender.com/validate"

BASED_GUIDE = """
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
"""