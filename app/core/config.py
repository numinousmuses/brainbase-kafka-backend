# app/core/config.py

DATABASE_URL = "sqlite:///./my_database.db" 

VALIDATION_ENDPOINT = "https://brainbase-engine-python.onrender.com/validate"

BASED_GUIDE = """
```markdown
# 简介 – 什么是 Brainbase？

**Brainbase** 是首创的 **企业代理平台（Enterprise Agent Platform, EAP）**，为大型企业 IT 团队提供了一个统一的平台来 **构建**、**部署** 并 **测试** 企业的 AI 劳动力。像 **丰田（Toyota）** 和 **NBC** 这样的公司会使用 Brainbase 在 **销售**、**市场营销** 和 **客户支持** 等领域构建各种代理，并将它们部署到 **电话**、**短信（SMS）**、**电子邮件**、**聊天** 等多种渠道。

我们核心的技术是 **Based 代理框架**，能让企业为其代理创造 **完全可靠、具备确定性行为** 的对话流程。这使得 Brainbase 在 **银行**、**医疗** 等关乎核心任务的、面向客户的应用场景下成为可行方案，而这类场景中我们的一些竞品往往因可靠性问题而难以满足要求。

---

## 什么是 Based？

**Based** 是一种高级的 AI 指令语言（High-level AI instruction language），专为打造 **在多种通信渠道上无缝运转的动态对话代理** 而设计。它为开发者提供了精妙且简洁的语法，让构建交互式流程变得高效而可靠。

### Based 的关键特性

- **直观且富有表现力的语法**  
  以清晰简洁的方式开发复杂对话逻辑。

- **针对对话的专用结构**  
  内置关键字 `talk`、`loop`、`until`、`ask`，以便轻松管理对话流程与状态。

- **跨平台的灵活性**  
  创建可部署于 **聊天**、**语音**、**电子邮件**、**短信**等多种渠道的代理，实现数据跨平台共享。

```

```python
# 在此处可插入任何 Pythonic 风格的 Based 代理示例代码
```

---

# Loop-Until

Based 的核心概念是对话循环（conversational loops）和交接（handoffs）。它将完整的对话流程拆分为便于管理的小片段，并在满足某些条件时将对话交接给其他代理。

**格式：**

```python
loop:
    res = talk("SYSTEM PROMPT FOR AGENT", True/False, {ANY INFO PASSED IN FROM PREVIOUS STEPS})
until "CONDITION 1":
    # OTHER AGENTS, CODE, ETC.
until "CONDITION 2":
    # OTHER AGENTS, CODE, ETC.
until ...
```

**规则：**

- **规则 1**：`loop` 中只能有一行，并且这一行必须是 `talk`。
- **规则 2**：每个 `until` 块的末尾都可以使用 `return` 将信息返回到 `talk` 所在的循环。如果在 `until` 块中没有使用 `return`，则不会返回到同一个 `talk` 循环，而是继续执行下一个 loop-until 流程。

**示例：**

```python
loop:
    res = talk("Talk to the user about the weather and try to learn about their city and where they'd want to see the weather at.", True)
until "user mentions a city":
    # 在这里调用 API 或其他集成来获取用户提及城市的天气
    # weather = ...
    return weather # 将信息返回给 talk 循环，使对话得以继续
```

在这个示例中，AI 会与用户聊天气，一直持续到用户提及了某个城市。随后，系统调用接口获取该城市的天气信息，并返回给对话循环，如此一来 AI 可以将天气信息反馈给用户。此后用户依旧处于相同的 `loop` 循环中，可再次提及其他城市并不断地循环下去。

**最佳实践**

- **实践 1**：在 `talk` 中编写 System Prompt 时，最好使用以下格式：
  - 明确代理的目的
  - 明确对话的风格
  - 说明退出（until）条件
  - 给出用户可能的示例对话或行为，以便引导从该 `talk` 切换到相应的 `until`
- **实践 2**：在 `talk` 中，可以通过第三个参数的字典形式传入在之前步骤中获取的上下文或信息：
  
  例如：`{"name": <上一步得到的用户姓名>, "age": <用户年龄>}`，或者更具业务场景的字典数据如 `{"order_no": <订单号>, "complaint_summary": <投诉概要>}` 等。

  注：要确保传递给代理的信息足够它完成工作，但避免在无关信息上过度堆砌。

---

# Subagent

在 Based 中最强大的能力之一，是能够调用子代理（subagent）执行某些 AI 任务。可以通过对任意在 Based 中定义的对象调用 `.ask` 方法来完成。

**格式：**

```python
info = some_object_from_before.ask(
    question="该子代理的目标，需描述清晰。",
    example={"name": "Brian Based", "previous_jobs": ["JOB 1", "JOB 2"]} # 返回的数据格式示例
)
```

**规则：**

- **规则 1**：`question` 要明确需要子代理完成的任务。例如：
  - 从用户输出中抽取 `name` 和 `age`
  - 总结用户所说的内容
  - 根据某些具体标准（需在问题中写明）进行情感打分，从 1（低）到 10（高）

- （同上）**规则 2**：每个 `until` 块的末尾可以通过 `return` 返回信息给 `talk` 循环，如果不使用 `return`，则不会再回到同一个 `talk` 循环。

**示例：**

```python
loop:
    res = talk("Talk to the user about the weather and try to learn about their city and where they'd want to see the weather at.", True)
until "user mentions a city":
    city_info = res.ask(question="Return the name of the city the user mentioned.", example={"city": "Boston"})
    # city_info 中现在包含{"city": "用户提及的城市"}，可在随后的流程或API调用中使用
    # weather = ...
    return weather # 将信息返回给 talk 循环，让代理继续和用户交互
```

**最佳实践**

- **实践 1**：尽量让 `.ask` 的 `question` 简洁明确
- **实践 2**：`example` 尽量详细，提供合理且能帮助子代理理解输出格式的示例数据
- **实践 3**：在 Based 中进行函数调用，通常是用 loop-until 和 ask 的组合方式：`until` 判断要执行哪个功能，`.ask` 获取本次要调用的功能所需的参数（如上示例中提取城市名称）。

---

# API 调用

Based 内置了两种主要方式用于向外部端点进行 `GET` 和 `POST` 请求。

**格式**

**GET 请求**

```python
res = api.get_req(
    url="URL ENDPOINT TO CALL",
    params={"a": "...", "b": "..."},
    headers={"Authentication": "..."}
)

# res: {"response": {...}} # 最终返回为字典数据
```

**POST 请求**

```python
res = api.post_req(
    url="URL ENDPOINT TO CALL",
    data={"a": "...", "b": "..."},
    headers={"Authentication": "..."}
)

# res: {"response": {...}} # 同样是字典数据
```

**最佳实践**

- **实践 1**：如果对返回数据的结构（schema）不清楚，可以结合子代理 `.ask` 生成自己需要的结构。例如：

  ```python
  res = api.post_req(
      url="URL ENDPOINT TO CALL",
      data={"a": "...", "b": "..."},
      headers={"Authentication": "..."}
  ) # 不确定返回结构
  info = res.ask(
      question="Return the name and address info from this result.",
      example={"name": "...", "address": "..."}
  ) # 通过子代理转换为 {"name": "...", "address": "..."} 等我们需要的结构
  ```

---

# 常见使用模式

以下是一些在 Based 中常见的使用模式示例。

## 分流（Triage）和处理

一个常见的模式是使用嵌套的 `loop-until` 来进行用户意图分流（triage）并收集所需信息。示例：

```python
loop:
    res = talk("I am a customer service agent. I can help with orders, returns, or general questions. Please let me know what you need help with.", True)
until "user mentions order":
    loop:
        res = talk("What is your order number?", True)
    until "user provides order number":
        # 处理与订单相关的请求
        return handle_order({"order_no": "order number from conversation"})
until "user mentions return":
    loop:
        res = talk("What is the order number you want to return and what is the reason?", True)
    until "user provides return details":
        # 处理退货请求
        return process_return({"order_no": "order number from conversation", "reason": "reason from conversation"})
until "general question":
    # 处理常规咨询
    return handle_general_query(res)
```

这种模式适用于：

- 根据用户输入跳转到不同的处理路径
- 在继续执行专门处理逻辑之前，先从用户处收集特定信息
- 在切换不同处理模式时保持对话上下文

## 顺序的 loop-until

另一个常见模式是在 Based 中使用一系列按顺序的 loop-until，用于依次收集多条信息。示例：

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

这种模式在以下情形中尤其有效：

- 需要按特定顺序收集信息
- 每条信息依赖或基于之前的用户回答
- 在获取多条信息的同时，仍然保证自然的对话流

当然，如果信息量很小也不必过分拆分。可以在同一次对话中收集多条信息，然后用一个 `until` 在检测到所有信息都已收集完毕时再退出循环。

---

# Based 快速入门 – 构建跨平台通用的对话代理

## 介绍
欢迎来到 **Based 快速入门**！本指南会向你介绍 **Based**——一门强大的领域专用编程语言，可用来构建跨平台的对话代理。你可以轻松地在聊天、语音、电子邮件、短信等渠道部署对话式流程，并在这些渠道间实现无缝数据交换及统一的用户体验。

---

## 什么是 Based？
**Based** 是一门高级 AI 指令语言，专注于设计 **可在多种通信渠道间无缝运转的动态对话代理**。它通过一种优雅、高抽象度的语法帮助开发者快速且可靠地构建交互式工作流。

### 关键特性
- **直观且富表现力的语法**：以更少代码实现更复杂的对话逻辑。  
- **专门的结构**：利用 `talk`、`loop`、`until`、`ask` 等内置关键字轻松管理对话流程和状态。  
- **跨平台灵活性**：可同时在聊天、语音、电子邮件、短信等渠道部署代理，并实现数据的无缝共享。

---

## 核心对话流结构

Based 脚本主要依赖以下三个关键字来构建交互式对话：

1. **`talk`**：发送消息或提示给用户并等待回复。（若第二个参数设为 `False`，则会先等待用户发信息）  
2. **`loop`**：开始一个可重复的对话块。  
3. **`until`**：指定在满足何种条件时结束该 `loop` 块。

在实际使用中，`talk` 通常被包裹在 `loop`/`until` 结构中。这样的设计可以让对话在满足条件前反复执行。

### 示例用法

```text
loop:
    # 询问用户首选的联系方式
    response = talk(
        "Hi there! What's your preferred contact method (email, phone, or SMS)?",
        True,
        {"preferred_contact": "email"} // 提供示例默认值
    )
until "User provides a valid contact method":
    contactInfo = response.ask(
        question="Extract and validate the contact method from the response.",
        example={"preferred_contact": "email"}
    )
    # 验证结果
    if contactInfo["preferred_contact"] not in ["email", "phone", "SMS"]:
        print("无效的联系方式。重新询问...")
    else:
        print("已获得有效的联系方式！")
```

```markdown
# Based 语言基础 – 核心结构参考

欢迎阅读 **Based 语言基础**指南。本参考文档详细说明了 **Based** 的核心语言结构、声明语法、参数及实际使用示例。熟悉这些基础概念，将帮助你更加自信且高效地构建强大的对话代理。

---

## 核心语言结构

Based 由一系列针对对话式 AI 工作流设计的专用结构组成。它们为构建复杂交互提供了高抽象度，确保不会在细节层面过度耗费精力。

---

## `say` 函数

`say` 函数会生成一段对用户的输出 **（不期待用户回复）**。常用来提供信息、指令或确认内容。

**语法：**
```text
say(message, exact=False, model=None)
```

**参数**：
- **message (string)**：要输出给用户的内容  
- **exact (boolean, 可选)**：控制输出方式  
  - **True**：输出内容与 `message` 完全相同  
  - **False**（默认）：允许 AI 在语义一致的前提下对 `message` 进行润色  
- **model (string, 可选)**：指定在 `exact=False` 时使用的 AI 模型

**返回值**：
- 返回生成的文本，可存储在变量中，也可仅用作直接输出

**示例**：
```text
# 使用确切信息跟用户打招呼
say("Welcome to BookBot! I'm here to help you find and reserve books.", exact=True)

# 根据意图生成动态欢迎语
say("Generate a friendly welcome for a user looking for book recommendations")

# 存储回复以便后续使用
intro = say("Introduce yourself as a helpful assistant", model="anthropic/claude-3.7-sonnet")
```

---

## `loop`、`talk` 与 `until` 模式

在 Based 中，`loop`、`talk` 和 `until` 一起使用，是 **必须** 遵循的基础模式。它们构建了一个可交互的对话流程，一旦满足特定条件就可退出循环。需要注意的是，**`talk` 并不单独使用**。

**语法：**
```text
loop:
    response = talk(
        system_prompt,
        first_prompt=True,
        default_values={},
        info={}
    )
until "对退出条件的描述":
    # 决定是否满足退出条件的验证逻辑
    # 如果条件未满足，则再次回到 loop 开始
```

### `talk` 的参数

- **system_prompt (string)**：指示或提示，指导对话内容
- **first_prompt (boolean, 可选)**：控制对话谁先说话
  - **True**（默认）：AI 先说
  - **False**：先等待用户说
- **default_values (dict, 可选)**：示例值，帮助规划期待的回复结构
- **info (dict, 可选)**：提供给对话的额外上下文

### Loop-Until 模式

1. **`loop`** 表示开始一个可重复的对话块  
2. 在 `loop` 中使用 **`talk`** 向用户提出问题并接收回答  
3. **`until`** 用自然语言描述在何种条件下结束循环  
4. `until` 块中执行检查：若条件满足，则退出循环；若不满足，则回到 `loop` 重新执行  
5. 如条件满足，则循环结束，继续向下执行

**示例**：
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

    # 检验有效性
    if preference_data["genre"] not in ["mystery", "sci-fi", "romance", "non-fiction"]:
        print("无效的类型。重新询问...")
        continue

    if preference_data["format"] not in ["paperback", "hardcover", "e-book", "audiobook"]:
        print("无效的格式。重新询问...")
        continue

    # 若执行到这里，表示 genre 和 format 都有效
    print("成功获取偏好！")
```

---

## 数据处理方法

Based 为 **转换或提取数据** 提供了强大的方法，且可用于任何数据对象，不局限于对话响应。

---

### `.ask` 方法

`.ask` 方法可从任意数据对象中提取结构化数据，将无结构信息转换为可编程使用的格式。可用于 API 响应、对话结果或任何其他数据。

**语法：**
```text
data_object.ask(question, example=None, schema=None, model=None)
```

**参数**：
- **question (string)**：关于所需信息的提问  
- **example (dict, 可选)**：输出格式的示例  
- **schema (dict, 可选)**：若要基于 JSON schema，可以在此提供  
- **model (string, 可选)**：执行提取操作时所用的 AI 模型

**返回值**：
- 返回与 `example` 或 `schema` 相符合的结构化数据

**示例**：
```text
# 从对话回复中提取用户阅读偏好
preferences = response.ask(
    question="Extract the user's preferred book genre, format, and any specific authors they mentioned.",
    example={
        "genre": "mystery",
        "format": "audiobook",
        "authors": ["Agatha Christie", "Arthur Conan Doyle"]
    }
)

# 对 API 响应使用 .ask
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

### `.summarize` 方法

`.summarize` 用于对任意数据对象进行简要概括，适用于文本块较大或数据结构复杂的场景。

**语法：**
```text
data_object.summarize(prompt=None, model=None)
```

**参数**：
- **prompt (string, 可选)**：可选地指定概括时的提要  
- **model (string, 可选)**：用于生成摘要的 AI 模型

**返回值**：
- 返回简明扼要的字符串摘要

**示例**：
```text
# 概括一篇冗长报告
document_content = document.read(url="https://example.com/lengthy-report.pdf")
summary = document_content.summarize(
    prompt="Provide a 3-paragraph summary of this financial report, focusing on key metrics and projections."
)

# 从搜索结果提取要点
search_results = google_search.search(query="latest developments in quantum computing")
key_points = search_results.summarize(
    prompt="Extract the 5 most significant recent breakthroughs in quantum computing mentioned in these results."
)
```

---

## 高级模式

### 多个 `until` 语句

Based 支持在同一个 `loop` 中使用 **多个 `until`**，从而实现更复杂的对话流。每个 `until` 块对应一个条件并触发各自的处理流程。

```text
# 示例：多条件对话处理
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
        # 处理查看订单状态
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
        # 处理退货
        say("I can help you process a return. Let me guide you through our return policy and steps.", exact=True)
        # 退货处理逻辑
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

### 条件性流程控制

可以结合标准的 Python 语法实现 **条件性流程控制**，从而依据用户回复动态地改变对话走向。

```text
# 根据用户对该类型的熟悉度和偏好来决定推荐方案
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

    # 个性化推荐方案
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
        # 高级读者
        recommendations = get_expert_recommendations(preferences["genre"])
        say(f"For an expert reader like yourself, these critically acclaimed {preferences['genre']} books offer complex narratives:", exact=True)

    # 展示前三个推荐
    for i, book in enumerate(recommendations[:3]):
        say(f"{i+1}. '{book['title']}' by {book['author']} - {book['description']}", exact=True)
```

---

## 面向具体平台的函数

Based 支持在 **聊天、语音、电子邮件、短信** 等多个平台上部署，同时提供了相应的函数以利用各自平台的特性。

---

### 语音部署函数

当你的 Based 代理部署在 **语音通话** 场景时，可使用以下函数：

1. **`transfer_call(phone_number)`**：将当前通话转接到另一个号码
   ```text
   # 若用户要求转人工
   if user_request["needs_human_support"]:
       say("I'll transfer you to our customer support team right away.", exact=True)
       transfer_call("+1-800-123-4567")
   ```

2. **`hangup()`**：结束当前电话
   ```text
   # 在完成订单后结束通话
   say("Thank you for your order! Your confirmation number is ABC123. Have a great day!", exact=True)
   hangup()
   ```

---

### 短信（SMS）部署函数

针对 **短信（SMS）** 部署，Based 提供以下特殊函数：

- **`send_image(url)`**：在会话中发送一张图片
  ```text
  # 在短信会话中发送产品图片
  product_details = get_product_info("ABC123")
  say(f"Here's the {product_details['name']} you inquired about:", exact=True)
  send_image(product_details["image_url"])
  ```

---

## 完整示例：图书推荐代理

下面是一个更完整的示例，它展示了多种 Based 语言结构如何协同工作，以及 **多个 `until`** 的使用：

```text
state = {}
meta_prompt = "You're a book recommendation assistant helping users find their next great read."
res = say("Hello! I'm BookBot, your personal book recommendation assistant.", exact=True)

# 简短介绍服务并告知用户期望
say("I can help you find books based on your preferences, including genre, format, and reading level.")

# 使用多个 until 分支来收集用户最初需求
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
        # 处理推荐流程
        state["intent"] = "recommendations"

        # 收集类别偏好
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

        # 调用 API 获取推荐
        recommendations = api.get_req(
            url='https://bookstore-api.example.com/recommendations',
            params=state["preferences"]
        ).ask(
            question="Extract the top 3 book recommendations with title, author, and description.",
            example={"books": [{"title": "Book Title", "author": "Author Name", "description": "Brief description"}]}
        )

        # 呈现推荐结果
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
        # 处理新书查询
        state["intent"] = "new_releases"
        genre = new_release_request.get("genre", "")

        # 获取新发行列表，可选按类别过滤
        new_releases = api.get_req(
            url='https://bookstore-api.example.com/new-releases',
            params={"genre": genre} if genre else {}
        ).ask(
            question="Extract the latest 5 book releases with title, author, and release date.",
            example={"books": [{"title": "New Book", "author": "Author Name", "release_date": "2023-10-15"}]}
        )

        # 呈现最新出版书单
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
        # 处理可用性查询
        state["intent"] = "check_availability"

        book_info = {}
        if "book_title" in availability_request:
            book_info["title"] = availability_request["book_title"]
        if "author" in availability_request:
            book_info["author"] = availability_request["author"]

        # 如果信息完整，直接检查可用性
        if "title" in book_info and "author" in book_info:
            availability = check_book_availability(book_info["title"], book_info["author"])
            if availability["available"]:
                say(f"Good news! '{book_info['title']}' by {book_info['author']} is available in these formats: {', '.join(availability['formats'])}", exact=True)
            else:
                say(f"I'm sorry, '{book_info['title']}' by {book_info['author']} is currently unavailable. Would you like me to notify you when it becomes available?", exact=True)
        else:
            # 需要更多信息
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

# 对话收尾
say("Is there anything else I can help you with today?", exact=True)
```

---

## 总结

**Based 语言** 提供了一个强大而直观的框架来构建对话式代理。只要掌握了最基本也最重要的 **`loop-talk-until`** 模式，你就能打造灵活且强大的对话流程，同时保持代码可读性与可维护性。

请记住，**Based** 旨在 **声明式** 地描述“想要实现什么”，而不必过于纠结“如何实现”。此方法可显著减少代码量并提高系统可靠性和可维护性。

当结合使用 **针对各平台的特殊函数** 时，你既能充分发挥每个平台（如语音、短信等）的能力，又可保持统一的代码库和用户体验。  
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