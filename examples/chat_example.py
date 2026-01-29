"""Example: Send chat completion requests using the inference gateway library."""

import asyncio

from inference_gateway import GatewayConfig, chat_completion


async def main():
    """Send a simple chat completion request."""
    # Configure the gateway
    config = GatewayConfig(
        text_base_url="http://localhost:8080",
        routing_mode="single",
    )

    # Prepare messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ]

    # Send request
    print("Sending chat completion request...")
    response = await chat_completion(
        messages,
        config,
        temperature=0.7,
        max_tokens=100,
    )

    # Extract and print the response
    assistant_message = response["choices"][0]["message"]["content"]
    print(f"\nAssistant: {assistant_message}")

    # Print token usage if available
    if "usage" in response:
        usage = response["usage"]
        print(f"\nTokens used: {usage.get('total_tokens', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
