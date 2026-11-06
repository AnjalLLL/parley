import asyncio
import os
from google import genai
from google.genai.types import LiveConnectConfig, Modality
from dotenv import load_dotenv

load_dotenv()

async def test_gemini_connectivity():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        print("Error: GEMINI_API_KEY not set in .env")
        return

    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-preview-09-2025")

    print(f"Connecting to Gemini ({model})...")
    try:
        async with client.aio.live.connect(
            model=model,
            config=LiveConnectConfig(response_modalities=[Modality.AUDIO])
        ) as session:
            print("Connected successfully!")
            
            # Send a simple text message to trigger a response
            print("Sending 'Hello'...")
            await session.send_client_content(turns={"role": "user", "parts": [{"text": "Hello, this is a connectivity test."}]}, turn_complete=True)
            
            async for message in session.receive():
                if message.data:
                    print(f"Received audio response: {len(message.data)} bytes")
                    break
                if message.server_content:
                    print("Received server content response.")
                    break
            
            print("Test passed!")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_connectivity())
