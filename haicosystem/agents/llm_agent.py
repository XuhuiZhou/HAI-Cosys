import logging

from sotopia.agents import LLMAgent
from sotopia.database import AgentProfile
from sotopia.messages import Observation

from haicosystem.generation_utils import (
    agenerate_action_bot,
    agenerate_action_human,
    validate_agentAction,
)
from haicosystem.protocols import HaiAgentAction, LangchainAgentAction

log = logging.getLogger("llm_agent")


class LLMAgentHuman(LLMAgent):
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

    async def aact(self, obs: Observation) -> HaiAgentAction:
        self.recv_message("Environment", obs)

        if len(obs.available_actions) == 1 and "none" in obs.available_actions:
            return HaiAgentAction(action_type="none", argument="")
        else:
            action = await agenerate_action_human(
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


class LLMAgentBot(LLMAgent):
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

    async def aact(self, obs: Observation) -> HaiAgentAction:
        self.recv_message("Environment", obs)
        if len(obs.available_actions) == 1 and "none" in obs.available_actions:
            return HaiAgentAction(action_type="none", argument="")
        else:
            action = await agenerate_action_bot(
                self.model_name,
                history="\n".join(f"{y.to_natural_language()}" for x, y in self.inbox),
                turn_number=obs.turn_number,
                action_types=obs.available_actions,
                agent=self.agent_name,
                goal=self.goal,
                script_like=self.script_like,
            )
            if action.action_type == "action":
                is_valid, corrected_action_argument = await validate_agentAction(
                    action, tool_output_parser=LangchainAgentAction
                )
                if not is_valid:
                    action.argument = corrected_action_argument

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
