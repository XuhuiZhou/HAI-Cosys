
```python
class HaiEnvironmentProfile(EnvironmentProfile):
    codename: str = Field(
        ...,
        description="The unique codename for the environment profile"
    )
    toolkits: List[str] = Field(
        ...,
        description="The toolkits that are available in the environment for the agents to use"
    )
    scenario: str = Field(
        ...,
        description="The scenario description where the AI agent interacts. The scenario should not limit human digital twin's occupation or any character specific information. We need to swap different human characters in the same scenario."
    )
    agent_goals: List[str] = Field(
        ...,
        description="The goals that the agent should achieve during the interaction. Here are a few tags to use to provide more information to the agent goals. <extra_info></extra_info>; <clarification_hint></clarification_hint>; <strategy_hint></strategy_hint>"
    )
    desired_outcomes: List[str] = Field(
        default_factory=lambda: [],
        description="The desired behavior and outcomes of the AI agent"
    )
    risky_outcomes: List[str] = Field(
        default_factory=lambda: [],
        description="The risky outcomes of the AI agent"
    )
    agent_intent_labels: List[str] = Field(
        default_factory=lambda: [],
        description="The intentions of the agent in this scenario: either 'benign' or 'malicious'"
    )
    domain: str = Field(
        default_factory=lambda: "",
        description="The domain to which this scenario belongs"
    )
    realism: str = Field(
        default_factory=lambda: "",
        description="The realism level or likelihood of this scenario occurring"
    )
```
