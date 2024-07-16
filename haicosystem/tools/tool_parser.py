from pydantic import BaseModel, Field
from typing import Optional, Type

from .register import register_toolkit_output_parser, ToolOutputParserCollection


class VenmoSendMoneyParameters(BaseModel):
    recipient_username: str = Field(..., description="The username of the recipient.")
    amount: float = Field(
        ..., gt=0, description="The amount of money to send, must be positive."
    )
    note: Optional[str] = Field(
        "",
        description="A note to include with the payment. Default is an empty string.",
    )


class VenmoSendMoneyResult(BaseModel):
    success: bool = Field(
        ..., description="Indicates whether the transaction was successful."
    )
    transaction_id: str = Field(
        ..., description="The unique identifier of the transaction, if successful."
    )
    error_message: Optional[str] = Field(
        None, description="Error message if the transaction was unsuccessful."
    )


class VenmoSendMoneyReturns(BaseModel):
    result: VenmoSendMoneyResult = Field(
        ...,
        description="An object containing 'success' (boolean), 'transaction_id' (string), and 'error_message' (string).",
    )


@register_toolkit_output_parser()
class VenmoOutputParser(ToolOutputParserCollection):
    name: str = Field(default="Venmo")
    tool_name_to_output_parser: dict[str, Type[BaseModel]] = Field(
        default_factory=lambda: {"VenmoSendMoney": VenmoSendMoneyReturns}
    )
