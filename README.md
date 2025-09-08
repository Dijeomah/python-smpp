
# Python SMPP Client

This is a simple SMPP client written in Python.

## Features

- Connect to an SMPP server.
- Send short messages.
- Automatic reconnection.

## How to Use

### 1. Configuration

Edit the `Test.py` file to configure the SMPP server details:

```python
config = SmppConfig()
config.account = "your_account"
config.password = "your_password"
config.server_ip = "localhost"
config.server_port = 2775
```

### 2. Running the Client

To run the client, execute the `Test.py` file:

```bash
python Test.py
```

### 3. Sending a Message

The `Test.py` file contains an example of how to send a message. You can modify the `submit_short_message` call to send your own message.

```python
client.conn.submit_short_message(
    service_type="",
    source_ton="UNKNOWN",
    source_npi="UNKNOWN",
    source_addr="12345",
    dest_ton="UNKNOWN",
    dest_npi="UNKNOWN",
    dest_addr="54321",
    esm_class=0,
    protocol_id=0,
    priority_flag=0,
    schedule_delivery_time="",
    validity_period="",
    registered_delivery=0,
    replace_if_present_flag=0,
    data_coding=0,
    sm_default_msg_id=0,
    short_message="Hello from Python!"
)
```

## Files

- `SmppConfig.py`: Configuration class for the SMPP client.
- `SmppClient.py`: The main SMPP client implementation.
- `SendSubmitSm.py`: Class to send a `submit_sm` PDU.
- `Response.py`: Class to handle SMPP responses.
- `MtnUssd.py`: Configuration and utility class for MTN USSD services.
- `Test.py`: Example of how to use the SMPP client.

