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
