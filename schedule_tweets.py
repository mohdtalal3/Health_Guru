import schedule
import time
import random
from twitter_poster import post_random_tweet

def job():
    """Function to be scheduled that posts a random tweet."""
    # Randomly vary the image probability between 0.6 and 0.8
    # This adds some natural variation to the tweet types
    image_probability = random.uniform(0.6, 0.8)
    post_random_tweet(image_probability=image_probability)
    print(f"Job completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """Main function to set up the schedule."""
    # Schedule the job to run at specific times
    # For example, post 3 times a day
    schedule.every().day.at("09:00").do(job)  # Morning tweet
    schedule.every().day.at("13:00").do(job)  # Afternoon tweet
    schedule.every().day.at("19:00").do(job)  # Evening tweet
    
    # You can also add some randomness to the schedule
    # For example, post once every 6-8 hours
    # schedule.every(6).to(8).hours.do(job)
    
    print("Tweet scheduler started. Press Ctrl+C to exit.")
    
    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # For testing, you can post a tweet immediately
    print("Posting an initial tweet...")
    job()
    
    # Then start the scheduler
    main() 