#!/usr/bin/env python3
"""Test client for HR Agent Chat API."""

import requests
import json
import sys


def test_chat_api(base_url: str = "http://localhost:8080"):
    """Test the HR Agent Chat API with various queries."""

    print(f"Testing HR Agent Chat API at {base_url}")
    print("=" * 60)

    # Test 1: Health check (root endpoint)
    print("\n1. Health Check")
    print("-" * 60)
    try:
        response = requests.get(f"{base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code == 200:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Test cases
    test_queries = [
        {
            "name": "Get Assignment ID - Valid User",
            "message": "What is the assignment ID for user nwaters?",
            "expected": "15778303"
        },
        {
            "name": "Get Assignment ID - Unknown User",
            "message": "What is the assignment ID for user unknown_person?",
            "expected": "not found"
        },
        {
            "name": "Get Timeoff Schedule",
            "message": "Get the timeoff schedule for assignment ID 15338303 from 2025-01-01 to 2025-12-31",
            "expected": "20250411"
        },
        {
            "name": "Get Direct Reports",
            "message": "Who are the direct reports for johndoe?",
            "expected": "nwaters"
        },
    ]

    headers = {
        "Content-Type": "application/json",
    }

    # Track session ID for conversation continuity
    session_id = None

    for i, test in enumerate(test_queries, start=2):
        print(f"\n{i}. {test['name']}")
        print("-" * 60)
        print(f"Message: {test['message']}")
        print(f"Expected: {test['expected']}")

        try:
            # Prepare request data
            request_data = {"message": test['message']}
            if session_id:
                request_data["session_id"] = session_id

            response = requests.post(
                f"{base_url}/chat",
                headers=headers,
                json=request_data,
                timeout=60
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                # Store session ID for continuity
                session_id = data.get('session_id')

                # Display response
                content = data.get('content', '')
                print(f"Response: {content[:200]}...")
                print(f"Session ID: {session_id}")
                print(f"Timestamp: {data.get('timestamp')}")
                print(f"Is New Session: {data.get('is_new_session')}")

                # Validate
                if test['expected'].lower() in content.lower():
                    print("✅ PASSED")
                else:
                    print("❌ FAILED - Expected text not found")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")

        except requests.exceptions.Timeout:
            print("❌ Request timed out")
        except Exception as e:
            print(f"❌ Error: {e}")

    # Test session retrieval
    if session_id:
        print(f"\n{len(test_queries) + 2}. Retrieve Session History")
        print("-" * 60)
        try:
            response = requests.get(f"{base_url}/sessions/{session_id}")
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Session ID: {data.get('session_id')}")
                print(f"Message Count: {data.get('message_count')}")
                print(f"SDK Session ID: {data.get('sdk_session_id')}")
                print("✅ PASSED")
            else:
                print("❌ FAILED")

        except Exception as e:
            print(f"❌ Error: {e}")

    # Test list all sessions
    print(f"\n{len(test_queries) + 3}. List All Sessions")
    print("-" * 60)
    try:
        response = requests.get(f"{base_url}/sessions")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Total Sessions: {data.get('total_sessions')}")
            print("✅ PASSED")
        else:
            print("❌ FAILED")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Chat API Testing Complete")
    print("=" * 60)


if __name__ == "__main__":
    # Parse command line arguments
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"

    # Run tests
    test_chat_api(base_url)
