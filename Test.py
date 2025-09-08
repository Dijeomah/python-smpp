
import logging
from SmppClient import SmppClient
from SmppConfig import SmppConfig

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    """
    Main function to run the SMPP client.
    """
    # Create a configuration object
    config = SmppConfig()
    config.account = "your_account"
    config.password = "your_password"
    config.server_ip = "localhost"
    config.server_port = 2775

    # Create an SMPP client
    client = SmppClient(config)

    try:
        # Connect to the SMPP gateway
        client.connect_gateway()

        if client.is_connected():
            logging.info("Successfully connected to the SMPP gateway.")

            # Send a sample message
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

            logging.info("Message sent successfully.")

        else:
            logging.error("Failed to connect to the SMPP gateway.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    finally:
        # Disconnect from the SMPP gateway
        if client.is_connected():
            client.disconnect()
            logging.info("Disconnected from the SMPP gateway.")


if __name__ == "__main__":
    main()

