#!/usr/bin/env python3
import asyncio
from rin.reminders import ReminderManager
import datetime

async def test_reminders():
    print("Testing ReminderManager...")
    
    # Initialize the manager
    mgr = ReminderManager()
    
    # Create a timer for a short period
    print("\n1. Creating a 10-second timer...")
    reminder = await mgr.set_timer(10, "Test Timer")
    if reminder:
        print(f"   Timer set with ID: {reminder['id']}")
        print(f"   Due at: {reminder['due_time']}")
    else:
        print("   Failed to set timer")
    
    # Create a reminder for a specific time
    print("\n2. Creating a reminder for 1 minute from now...")
    now = datetime.datetime.now()
    due_time = now + datetime.timedelta(minutes=1)
    reminder = await mgr.set_reminder(due_time.isoformat(), "Test Reminder")
    if reminder:
        print(f"   Reminder set with ID: {reminder['id']}")
        print(f"   Due at: {reminder['due_time']}")
    else:
        print("   Failed to set reminder")
    
    # List all active reminders
    print("\n3. Listing all active reminders...")
    reminders = await mgr.get_reminders()
    if reminders:
        for i, r in enumerate(reminders):
            print(f"   {i+1}. {r['type'].capitalize()}: {r['description']} (ID: {r['id']})")
            print(f"      Due at: {r['due_time']}")
    else:
        print("   No active reminders found")
    
    # Wait for the first notification
    print("\n4. Waiting for timer notification (10 seconds)...")
    # Wait for a bit less than the timer to avoid race conditions
    await asyncio.sleep(5)
    
    # List reminders again (should still have the 1-minute reminder)
    reminders = await mgr.get_reminders()
    if reminders:
        print("\n5. Remaining reminders:")
        for i, r in enumerate(reminders):
            print(f"   {i+1}. {r['type'].capitalize()}: {r['description']} (ID: {r['id']})")
            
            # Cancel this reminder
            if i == 0:  # Cancel the first remaining reminder
                reminder_id = r['id']
                print(f"\n6. Cancelling reminder with ID: {reminder_id}")
                success = await mgr.cancel_reminder(reminder_id)
                print(f"   Cancellation {'successful' if success else 'failed'}")
    else:
        print("\n5. No remaining reminders found")
    
    # Final list should be empty
    reminders = await mgr.get_reminders()
    print(f"\n7. Final reminder count: {len(reminders)}")
    
    print("\nReminder test completed!")

if __name__ == "__main__":
    asyncio.run(test_reminders()) 