import json
import re
import logging
from sotopia.agents import LLMAgent
from sotopia.database import AgentProfile
from sotopia.messages import AgentAction, Observation, ActionType
from langchain.output_parsers import PydanticOutputParser
import gin
from beartype import beartype
from sotopia.generation_utils.generate import (
    agenerate,
    agenerate_goal,
    agenerate_action,
    obtain_chain,
)
from sotopia.generation_utils.langchain_callback_handler import LoggingCallbackHandler

log = logging.getLogger("llm_agent")
logging_handler = LoggingCallbackHandler("langchain")


@gin.configurable
@beartype
async def agenerate_action_x(
    model_name: str,
    history: str,
    turn_number: int,
    action_types: list[ActionType],
    agent: str,
    goal: str,
    temperature: float = 0.7,
    script_like: bool = False,
) -> AgentAction:
    """
    Generate the action for the agent, only should be used for generating human-like actions
    """
    try:
        if script_like:
            # model as playwright
            raise NotImplementedError(
                "Not implemented yet for script_like mode in agenerate_action_x"
            )
        else:
            # Normal case, model as agent
            template = """
                Imagine you are {agent}, your task is to act/speak as {agent} would, keeping in mind {agent}'s social goal.
                You can find {agent}'s goal (or background) in the 'Here is the context of the interaction' field.
                Note that {agent}'s goal is only visible to you.
                You should try your best to achieve {agent}'s goal in a way that align with their character traits.
                Additionally, maintaining the conversation's naturalness and realism is essential (e.g., do not repeat what other people has already said before).
                Remember that you are a human in this conversation, and human try to keep their output short and to the point. Just imagine every character you type costs you energy and time. Your output should usually not exceed 10 words in one turn. But feel free to use more words if necessary.
                {history}.
                You are at Turn #{turn_number}. Your available action types are
                {action_list}.
                Note: You can "leave" this conversation if 1. you have achieved your social goals, 2. this conversation makes you uncomfortable, 3. you find it uninteresting/you lose your patience, 4. or for other reasons you want to leave.

                Please only generate a JSON string including the action type and the argument.
                Your action should follow the given format:
                {format_instructions}
            """
        return await agenerate(
            model_name=model_name,
            template=template,
            input_values=dict(
                agent=agent,
                turn_number=str(turn_number),
                history=history,
                action_list=" ".join(action_types),
            ),
            output_parser=PydanticOutputParser(pydantic_object=AgentAction),
            temperature=temperature,
        )
    except Exception:
        return AgentAction(action_type="none", argument="")


class LLMAgentX(LLMAgent):
    """
    This agent should only be used for simulating human characters in the environment.
    """

    def __init__(
        self,
        agent_name: str | None = None,
        uuid_str: str | None = None,
        agent_profile: AgentProfile | None = None,
        model_name: str = "gpt-3.5-turbo",
        script_like: bool = False,
    ) -> None:
        super().__init__(
            agent_name=agent_name,
            uuid_str=uuid_str,
            agent_profile=agent_profile,
            model_name=model_name,
            script_like=script_like,
        )

    async def aact(self, obs: Observation) -> AgentAction:
        self.recv_message("Environment", obs)

        if len(obs.available_actions) == 1 and "none" in obs.available_actions:
            return AgentAction(action_type="none", argument="")
        else:
            action = await agenerate_action_x(
                self.model_name,
                history="\n".join(f"{y.to_natural_language()}" for x, y in self.inbox),
                turn_number=obs.turn_number,
                action_types=obs.available_actions,
                agent=self.agent_name,
                goal=self.goal,
                script_like=self.script_like,
            )
            # Temporary fix for mixtral-moe model for incorrect generation format
            if "Mixtral-8x7B-Instruct-v0.1" in self.model_name:
                current_agent = self.agent_name
                if f"{current_agent}:" in action.argument:
                    print("Fixing Mixtral's generation format")
                    action.argument = action.argument.replace(f"{current_agent}: ", "")
                elif f"{current_agent} said:" in action.argument:
                    print("Fixing Mixtral's generation format")
                    action.argument = action.argument.replace(
                        f"{current_agent} said: ", ""
                    )
            return action


def format_bad_output_tool(
    ill_formed_output: str,
    model_name: str = "gpt-3.5-turbo",
) -> str:
    template = """
    Given the string that can not be parsed by json parser, reformat it to a string that can be parsed by json parser.
    Original string: {ill_formed_output}

    Please only generate the JSON:
    """
    chain = obtain_chain(
        model_name=model_name,
        template=template,
        input_variables=re.findall(r"{(.*?)}", template),
    )
    input_values = {
        "ill_formed_output": ill_formed_output,
    }
    reformat = chain.predict([logging_handler], **input_values)
    log.info(f"Reformated output: {reformat}")
    return reformat


class LLMAgentY(LLMAgent):
    """
    This agent should only be used for simulating agent characters in the environment.
    """

    def __init__(
        self,
        agent_name: str | None = None,
        uuid_str: str | None = None,
        agent_profile: AgentProfile | None = None,
        model_name: str = "gpt-3.5-turbo",
        script_like: bool = False,
    ) -> None:
        super().__init__(
            agent_name=agent_name,
            uuid_str=uuid_str,
            agent_profile=agent_profile,
            model_name=model_name,
            script_like=script_like,
        )

    async def aact(self, obs: Observation) -> AgentAction:
        self.recv_message("Environment", obs)

        if self._goal is None:
            self._goal = await agenerate_goal(
                self.model_name,
                background=self.inbox[0][
                    1
                ].to_natural_language(),  # Only consider the first message for now
            )

        if len(obs.available_actions) == 1 and "none" in obs.available_actions:
            return AgentAction(action_type="none", argument="")
        else:
            action = await agenerate_action(
                self.model_name,
                history="\n".join(f"{y.to_natural_language()}" for x, y in self.inbox),
                turn_number=obs.turn_number,
                action_types=obs.available_actions,
                agent=self.agent_name,
                goal=self.goal,
                script_like=self.script_like,
            )
            if action.action_type == "action":
                try:
                    json.loads(action.argument)
                except Exception as e:
                    log.debug(
                        f"[red] Failed to parse result: {action.argument}\nEncounter Exception {e}\nstart to reparse",
                        extra={"markup": True},
                    )
                    reformat_parsed_result = format_bad_output_tool(action.argument)
                    action.argument = reformat_parsed_result

            # Temporary fix for mixtral-moe model for incorrect generation format
            if "Mixtral-8x7B-Instruct-v0.1" in self.model_name:
                current_agent = self.agent_name
                if f"{current_agent}:" in action.argument:
                    print("Fixing Mixtral's generation format")
                    action.argument = action.argument.replace(f"{current_agent}: ", "")
                elif f"{current_agent} said:" in action.argument:
                    print("Fixing Mixtral's generation format")
                    action.argument = action.argument.replace(
                        f"{current_agent} said: ", ""
                    )

            return action
