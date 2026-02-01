import schedule
import time
import subprocess
import random
from datetime import datetime, timedelta

def run_pipeline():
    print("Running pipeline...")
    subprocess.run(["python", "main.py"])

def schedule_random_times():
    # Clear existing jobs
    schedule.clear()

    # Schedule 1-3 random times per day, between 8 AM and 10 PM, avoiding 2-6 AM
    num_posts = random.randint(1, 3)
    for _ in range(num_posts):
        hour = random.choice([h for h in range(8, 22) if not (2 <= h <= 6)])
        minute = random.randint(0, 59)
        time_str = f"{hour:02d}:{minute:02d}"
        schedule.every().day.at(time_str).do(run_pipeline)
        print(f"Scheduled post at {time_str}")

# Initial schedule
schedule_random_times()

print("Scheduler started with randomized times.")

# Reschedule daily at midnight
schedule.every().day.at("00:00").do(schedule_random_times)

while True:
    schedule.run_pending()
    time.sleep(60)