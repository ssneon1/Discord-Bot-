import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient, whoami

load_dotenv()

token = os.getenv("HUGGING_FACE_TOKEN")
print(f"Token present: {bool(token)}")

if not token:
    print("No token found")
    exit(1)

try:
    print("\n--- Validating Token ---")
    user_info = whoami(token=token)
    print(f"Token is VALID.")
    print(f"User: {user_info.get('name')}")
    print(f"Org memberships: {user_info.get('orgs')}")
    print(f"Auth type: {user_info.get('auth', {}).get('type')}")
    # Inspect capabilities if available in response
except Exception as e:
    print(f"Token validation FAILED: {e}")
    # Still try to continue

client = InferenceClient(token=token)


print("\n--- Testing Models ---")

# Test 1: Llama 3.2 with chat_completion (User's use case)
model = "meta-llama/Llama-3.2-1B-Instruct"
print(f"\nTesting {model} (chat_completion)...")
try:
    resp = client.chat_completion(
        messages=[{"role": "user", "content": "Hello!"}],
        model=model,
        max_tokens=50
    )
    print(f"✅ SUCCESS with {model}!")
    print(f"Response: {resp.choices[0].message.content}")
except Exception as e:
    print(f"❌ FAILED with {model}:")
    print(f"Error: {repr(e)}")

# Test 2: GPT2 with text_generation (Baseline)
model = "gpt2"
print(f"\nTesting {model} (text_generation)...")
try:
    resp = client.text_generation("Hello!", model=model, max_new_tokens=20)
    print(f"✅ SUCCESS with {model}!")
    print(f"Response: {resp}")
except Exception as e:
    print(f"❌ FAILED with {model}:")
    print(f"Error: {repr(e)}")

