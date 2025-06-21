#!/usr/bin/env python3
"""
Debug script to investigate why only 1 question is saved when 11 are imported.
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def check_questions_in_memory():
    """Check what questions are actually in memory."""
    print("🔍 Checking questions in memory...")
    try:
        response = requests.get(f"{BASE_URL}/api/debug/questions")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                debug_info = data['debug_info']
                print(f"📊 Total questions in memory: {debug_info['total_questions']}")
                print(f"📋 Questions type: {debug_info['questions_type']}")
                
                print("\n🔍 Sample questions:")
                for q_info in debug_info['sample_questions']:
                    print(f"  Question {q_info['index']}:")
                    print(f"    Type: {q_info['type']}")
                    if 'tuple_content' in q_info:
                        tc = q_info['tuple_content']
                        print(f"    Text: {tc['question_text'][:50]}...")
                        print(f"    Options: {tc['options_count']}")
                        print(f"    Category: {tc['category']}")
                    print()
            else:
                print(f"❌ Debug failed: {data.get('error')}")
        else:
            print(f"❌ Debug request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Memory check error: {e}")

def check_saved_file():
    """Check what's actually in the saved file."""
    print("📁 Checking saved questions file...")
    try:
        with open('data/questions.json', 'r') as f:
            saved_questions = json.load(f)
        
        print(f"💾 Questions in file: {len(saved_questions)}")
        
        if saved_questions:
            print("\n📝 First few questions in file:")
            for i, q in enumerate(saved_questions[:3]):
                print(f"  Question {i+1}:")
                print(f"    Text: {q.get('question_text', 'N/A')[:50]}...")
                print(f"    Options: {len(q.get('options', []))}")
                print(f"    Category: {q.get('category', 'N/A')}")
                print()
        
        return len(saved_questions)
    except FileNotFoundError:
        print("❌ No questions file found")
        return 0
    except Exception as e:
        print(f"❌ File check error: {e}")
        return 0

def test_manual_save():
    """Test the save functionality manually."""
    print("💾 Testing manual save...")
    try:
        response = requests.post(f"{BASE_URL}/api/refresh")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Refresh successful: {data.get('message')}")
                print(f"📊 Total questions: {data.get('total_questions')}")
            else:
                print(f"❌ Refresh failed: {data.get('error')}")
        else:
            print(f"❌ Refresh request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Manual save test error: {e}")

def create_test_file():
    """Create a small test file to import."""
    test_data = """# Questions

**Q1.** (Test Category)
What is a test question?
   A. Option A
   B. Option B
   C. Option C
   D. Option D

**Q2.** (Test Category)
What is another test question?
   A. Option A
   B. Option B
   C. Option C
   D. Option D

---

# Answers

**A1.** A
**A2.** B
"""
    
    with open('test_small.md', 'w') as f:
        f.write(test_data)
    
    print("📝 Created test_small.md with 2 questions")
    return 'test_small.md'

def test_small_import():
    """Test importing a small file to isolate the issue."""
    print("\n🧪 Testing small file import...")
    
    # Create test file
    filename = create_test_file()
    
    try:
        # Import the test file
        with open(filename, 'rb') as f:
            files = {'file': (filename, f, 'text/markdown')}
            response = requests.post(f"{BASE_URL}/import/questions", files=files)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Small import successful: {data.get('message')}")
                print(f"📊 Added: {data.get('total_added')}")
                
                # Check memory and file
                print("\n🔍 After small import:")
                check_questions_in_memory()
                file_count = check_saved_file()
                
                print(f"\n📊 Summary:")
                print(f"   Imported: {data.get('total_added')}")
                print(f"   In file: {file_count}")
                
                if data.get('total_added') != file_count:
                    print("❌ MISMATCH: Import count != saved count")
                else:
                    print("✅ Import and save counts match")
                    
            else:
                print(f"❌ Small import failed: {data.get('error')}")
        else:
            print(f"❌ Small import request failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Small import test error: {e}")

def main():
    """Main debug function."""
    print("🔍 Debug Script: Import vs Save Mismatch")
    print("=" * 50)
    
    # Check server
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        if response.status_code != 200:
            print("❌ Server not responding")
            return
        print("✅ Server is running\n")
    except:
        print("❌ Cannot connect to server")
        return
    
    # Check current state
    print("1. Current state check:")
    check_questions_in_memory()
    initial_file_count = check_saved_file()
    
    print(f"\n2. Testing with small file:")
    test_small_import()
    
    print(f"\n3. Manual save test:")
    test_manual_save()
    final_file_count = check_saved_file()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS:")
    print(f"   Initial file count: {initial_file_count}")
    print(f"   Final file count: {final_file_count}")
    
    if final_file_count > initial_file_count:
        print("✅ Save functionality appears to be working")
    else:
        print("❌ Save functionality has issues")
    
    print("\n💡 Next steps:")
    print("   1. Check the server logs during import")
    print("   2. Look for specific error messages in the save process")
    print("   3. Verify question format consistency")

if __name__ == "__main__":
    main()