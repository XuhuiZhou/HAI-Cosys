def format_tool_prompt(
    tool_names: str,
    toolkit_descriptions: str,
) -> str:
    """Format tool prompts"""
    return f"""
Tools to use when issuing an action:
[Tool Specifications]
Each toolkit is a collection of relevant tools for completing a specific task. Each tool is specified by:
1. Arguments: The tool input argument specification
2. Returns: The tool output return specification

The following tools are available:
{tool_names}

Here are the descriptions of the toolkits:
{toolkit_descriptions}

- [Format Instructions for the Agent]:

Basically [Agent] needs to provide a json string that fits into the following class structure:
```python
class AgentAction(Serializable):
    "A full description of an action for an ActionAgent to execute."

    tool: str
    "The name of the Tool to execute."
    tool_input: Union[str, dict]
    "The input to pass in to the Tool."
    log: str
    "Additional information to log about the action.
    This log can be used in a few ways. First, it can be used to audit
    what exactly the LLM predicted to lead to this (tool, tool_input).
    Second, it can be used in future iterations to show the LLMs prior
    thoughts. This is useful when (tool, tool_input) does not contain
    full information about the LLM prediction (for example, any `thought`
    before the tool/tool_input)."
```
The output should look like this:
```json
{{
    "action_type": "action",
    "argument": {{
        "log": "log"
        "tool": "tool_name",
        "tool_input": {{"arg1": "value1", "arg2": "value2"}},
    }}
}}
```

- Format Requirements for the [Agent]:
Here are some requirements that [Agent] should strictly follow to format the [tool] and [tool_input]:
1. **Use only available tools**: Do not use tools that are not provided above. In particular, do not use None or N/A as the value of the tool. If [Agent] cannot (or do not need to) use any existing tools to improve [Agent]'s response, conclude by stating [Final Answer] directly.
2. **Single JSON object**: Ensure the [tool_input] is a single JSON object that strictly follows the specification of the tool's [Arguments]. Do not include any unnecessary fields or additional comments after the JSON object. Do not include any backsticks to wrap the JSON object.
    - Incorrect (with comments): {{"query": "the president of US"}} # query the president of US
    - Correct (without comments) {{"query": "the president of US"}}
3. **Avoid using placeholders**: Do not use vague input values with placeholders. Instead, first obtain the actual values for the placeholders (using other tools if necessary) and then use them in the input.
    - Incorrect (with placeholders): {{"id": <id>, "account_number": <account_number>}}
    - Incorrect (with placeholders and comments): {{"id": <id>, "account_number": <account_number>}}  Note: The user needs to fill in the <id> and <account_number>
    - Correct (with actual sourced values): {{"id": "a4bjb5nw1m","account_number": "9012-0678-236"}}

- Format Examples for [Agent]:
Here is an example for how to format [Agent]'s response. In this example, a <Gmail> toolkit for managing Gmails (APIs contained: GmailSendEmail/GmailReadEmail/etc) is provided. Detailed tool specification is omitted here.

User input: Send an email to John Lee (johnlee@gmail.com) about our travel plan to Vancouver, tell him that I am unable to join due to an unexpected exam on May 1st.
"log": The user wants to inform John Lee about their travel plan to Vancouver but is unable to join due to an exam on May 1st. They want to send an email to John Lee for this purpose.
"tool": "GmailSendEmail"
"tool_input": {{"subject": "Unable to join for Vancouver trip", "body": "Hi John,

I hope this email finds you well. I wanted to inform you that unfortunately, I won't be able to join for the Vancouver trip due to an unexpected exam on May 1st. I apologize for any inconvenience this may cause.

Best regards", "to": "johnlee@gmail.com"}}
Observation: {{"status": "Success"}}
"""
