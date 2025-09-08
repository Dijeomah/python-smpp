
import logging
from SmppClient import SmppClient
from SmppConfig import SmppConfig
import smpplib.consts

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

        logging.info("Successfully connected to the SMPP gateway.")

        # Send a sample message
        client.submit_short_message(
            source_addr="12345",
            destination_addr="54321",
            short_message="Hello from Python!",
            source_addr_ton=smpplib.consts.SMPP_TON_INTL,
            source_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
            dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
            dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
            data_coding=smpplib.consts.SMPP_ENCODING_DEFAULT,
        )

        logging.info("Message sent successfully.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    finally:
        # Disconnect from the SMPP gateway
        client.disconnect()
        logging.info("Disconnected from the SMPP gateway.")


if __name__ == "__main__":
    main()

