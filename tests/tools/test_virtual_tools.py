from haicosystem.tools import ToolRegistry

def test_venmo_send_money() -> None:
    venmo_send_money = ToolRegistry.registry["venmo"]["venmo_send_money"]

    result = venmo_send_money.call(
        {
            "recipient_username": "user",
            "amount": "10",
            "note": "Splitting the bill for last night's seafood dinner.",
        }
    )

    assert result.result.status == "ok"
    assert result.result.output.json() == "{\"success\": true, \"transaction_id\": \"123456\", \"error_message\": null}"