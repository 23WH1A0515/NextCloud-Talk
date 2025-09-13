import requests
import sys
import json
from datetime import datetime

class NextTalkDashAPITester:
    def __init__(self, base_url="https://quickchat-dash.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.room_ids = []
        self.message_ids = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, list) and len(response_data) > 0:
                        print(f"   Response: {len(response_data)} items returned")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_api_root(self):
        """Test API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET", 
            "",
            200
        )
        return success

    def test_get_rooms(self):
        """Test getting all rooms"""
        success, response = self.run_test(
            "Get Rooms",
            "GET",
            "rooms",
            200
        )
        if success and isinstance(response, list):
            self.room_ids = [room['id'] for room in response]
            print(f"   Found {len(response)} rooms: {[r['name'] for r in response]}")
            # Verify room structure
            for room in response:
                required_fields = ['id', 'name', 'participants', 'unread_count']
                missing_fields = [field for field in required_fields if field not in room]
                if missing_fields:
                    print(f"   ⚠️  Room missing fields: {missing_fields}")
        return success

    def test_get_messages(self):
        """Test getting messages for each room"""
        if not self.room_ids:
            print("❌ No room IDs available for message testing")
            return False
        
        all_success = True
        for room_id in self.room_ids:
            success, response = self.run_test(
                f"Get Messages for Room {room_id}",
                "GET",
                f"rooms/{room_id}/messages",
                200
            )
            if success and isinstance(response, list):
                self.message_ids.extend([msg['id'] for msg in response])
                print(f"   Found {len(response)} messages in room {room_id}")
                # Verify message structure
                for msg in response:
                    required_fields = ['id', 'room_id', 'sender_name', 'content', 'timestamp']
                    missing_fields = [field for field in required_fields if field not in msg]
                    if missing_fields:
                        print(f"   ⚠️  Message missing fields: {missing_fields}")
            else:
                all_success = False
        
        return all_success

    def test_send_message(self):
        """Test sending a new message"""
        if not self.room_ids:
            print("❌ No room IDs available for message sending")
            return False
        
        test_room_id = self.room_ids[0]
        test_message = f"Test message from API test - {datetime.now().strftime('%H:%M:%S')}"
        
        success, response = self.run_test(
            "Send Message",
            "POST",
            "messages",
            200,
            data={
                "room_id": test_room_id,
                "content": test_message
            }
        )
        
        if success and 'id' in response:
            self.message_ids.append(response['id'])
            print(f"   Created message with ID: {response['id']}")
            
            # Verify the message appears in room messages
            verify_success, verify_response = self.run_test(
                "Verify Sent Message",
                "GET",
                f"rooms/{test_room_id}/messages",
                200
            )
            
            if verify_success:
                sent_message = next((msg for msg in verify_response if msg['content'] == test_message), None)
                if sent_message:
                    print(f"   ✅ Message verified in room messages")
                else:
                    print(f"   ⚠️  Sent message not found in room messages")
        
        return success

    def test_add_reaction(self):
        """Test adding emoji reactions to messages"""
        if not self.message_ids:
            print("❌ No message IDs available for reaction testing")
            return False
        
        test_message_id = self.message_ids[0]
        test_emoji = "👍"
        
        success, response = self.run_test(
            "Add Reaction",
            "POST",
            "reactions",
            200,
            data={
                "message_id": test_message_id,
                "emoji": test_emoji
            }
        )
        
        if success and response.get('success'):
            print(f"   ✅ Reaction added successfully")
        
        return success

    def test_get_summary(self):
        """Test getting AI chat summary for each room"""
        if not self.room_ids:
            print("❌ No room IDs available for summary testing")
            return False
        
        all_success = True
        for room_id in self.room_ids:
            success, response = self.run_test(
                f"Get Summary for Room {room_id}",
                "GET",
                f"summary/{room_id}",
                200
            )
            if success:
                required_fields = ['summary_points', 'message_count', 'time_range']
                missing_fields = [field for field in required_fields if field not in response]
                if missing_fields:
                    print(f"   ⚠️  Summary missing fields: {missing_fields}")
                else:
                    print(f"   Summary has {len(response['summary_points'])} points")
            else:
                all_success = False
        
        return all_success

    def test_mark_room_read(self):
        """Test marking room as read"""
        if not self.room_ids:
            print("❌ No room IDs available for mark-read testing")
            return False
        
        test_room_id = self.room_ids[0]
        
        success, response = self.run_test(
            "Mark Room as Read",
            "POST",
            f"rooms/{test_room_id}/mark-read",
            200
        )
        
        if success and response.get('success'):
            print(f"   ✅ Room marked as read successfully")
        
        return success

def main():
    print("🚀 Starting NextTalk Dash API Tests")
    print("=" * 50)
    
    tester = NextTalkDashAPITester()
    
    # Run all tests in sequence
    test_results = []
    
    test_results.append(("API Root", tester.test_api_root()))
    test_results.append(("Get Rooms", tester.test_get_rooms()))
    test_results.append(("Get Messages", tester.test_get_messages()))
    test_results.append(("Send Message", tester.test_send_message()))
    test_results.append(("Add Reaction", tester.test_add_reaction()))
    test_results.append(("Get Summary", tester.test_get_summary()))
    test_results.append(("Mark Room Read", tester.test_mark_room_read()))
    
    # Print final results
    print("\n" + "=" * 50)
    print("📊 FINAL TEST RESULTS")
    print("=" * 50)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📈 Overall: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All API tests passed!")
        return 0
    else:
        print("⚠️  Some API tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())