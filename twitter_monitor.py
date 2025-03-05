import tweepy
import json
import time
import threading
import queue
import random
import datetime
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ai_utils import generate_reply
from twitter_poster import load_config, initialize_twitter_client
from datetime import timedelta, timezone

# Set up logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("twitter_monitor.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("twitter_monitor")

# Queue for storing tweets to reply to
reply_queue = queue.Queue()

# Keep track of tweets we've already processed
processed_tweets = set()

# Rate limiting variables
last_api_call = 0
min_time_between_calls = 2  # seconds between API calls

# Define retry decorator for Twitter API calls
# This will retry on rate limit errors with exponential backoff
twitter_retry = retry(
    retry=retry_if_exception_type(tweepy.errors.TooManyRequests),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda retry_state: logger.warning(
        f"Rate limit hit, waiting {retry_state.next_action.sleep} seconds before retry {retry_state.attempt_number}"
    )
)

# File to store processed tweets
PROCESSED_TWEETS_FILE = "processed_tweets.json"

def load_processed_tweets():
    """Load the list of processed tweet IDs from file."""
    try:
        if os.path.exists("processed_tweets.json"):
            with open("processed_tweets.json", "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            logger.info("No processed tweets file found, creating a new one")
            return []
    except Exception as e:
        logger.error(f"Error loading processed tweets: {e}")
        return []

def save_processed_tweets(processed_tweets):
    """Save the list of processed tweet IDs to file."""
    try:
        # Keep only the most recent 1000 tweets to avoid the file growing too large
        if len(processed_tweets) > 1000:
            processed_tweets = processed_tweets[-1000:]
        
        with open("processed_tweets.json", "w", encoding="utf-8") as f:
            json.dump(processed_tweets, f)
        logger.debug(f"Saved {len(processed_tweets)} processed tweets")
    except Exception as e:
        logger.error(f"Error saving processed tweets: {e}")

def load_monitoring_config():
    """Load the monitoring configuration from the prompts template file."""
    try:
        with open("prompts_template_alex.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("monitoring", {})
    except Exception as e:
        logger.error(f"Error loading monitoring config: {e}")
        return {}

def get_hashtag_query():
    """Generate a query string for the hashtags to monitor."""
    monitoring_config = load_monitoring_config()
    hashtags = monitoring_config["hashtags"]
    return " OR ".join(hashtags)

def get_keyword_query():
    """Get a search query for keywords from a random category."""
    # Load monitoring configuration
    config = load_monitoring_config()
    
    # Get keyword categories
    keyword_categories = config.get("keywords", {})
    if not keyword_categories:
        logger.warning("No keyword categories found in monitoring config")
        return "", ""
    
    # Instead of using all keywords, select one random category
    category_name = random.choice(list(keyword_categories.keys()))
    keywords = keyword_categories[category_name]
    
    logger.info(f"Selected keyword category: {category_name} with {len(keywords)} keywords")
    
    # Build the query
    query = " OR ".join([f'"{keyword}"' for keyword in keywords])
    
    # Add language filter
    query += " lang:en"
    
    return query, category_name

def respect_rate_limit():
    """Sleep if necessary to respect the rate limit."""
    global last_api_call
    current_time = time.time()
    time_since_last_call = current_time - last_api_call
    
    if time_since_last_call < min_time_between_calls:
        sleep_time = min_time_between_calls - time_since_last_call
        time.sleep(sleep_time)
    
    last_api_call = time.time()

@twitter_retry
def safe_get_users_mentions(client, user_id, max_results=10):
    """Safely get user mentions with retry logic."""
    respect_rate_limit()
    return client.get_users_mentions(
        id=user_id,
        max_results=max_results,
        tweet_fields=["author_id", "created_at", "conversation_id"]
    )

@twitter_retry
def safe_get_tweet(client, tweet_id):
    """Safely get a tweet with retry logic."""
    respect_rate_limit()
    return client.get_tweet(tweet_id, tweet_fields=["author_id", "created_at", "conversation_id"])

@twitter_retry
def safe_search_recent_tweets(client, query, max_results=20):
    """Safely search for recent tweets with retry logic."""
    respect_rate_limit()
    return client.search_recent_tweets(
        query=query,
        max_results=max_results,
        tweet_fields=["author_id", "created_at", "conversation_id"]
    )

@twitter_retry
def safe_create_tweet(client, text, in_reply_to_tweet_id=None):
    """Safely create a tweet with retry logic."""
    respect_rate_limit()
    return client.create_tweet(text=text, in_reply_to_tweet_id=in_reply_to_tweet_id)

@twitter_retry
def safe_get_friendship(api, source_id, target_id):
    """Safely get friendship status with retry logic."""
    respect_rate_limit()
    return api.get_friendship(source_id=source_id, target_id=target_id)

def monitor_mentions(client, api, user_id):
    """Monitor Twitter for mentions and add them to the reply queue."""
    logger.info("Starting mentions monitoring thread")
    
    # Load processed tweets
    processed_tweets = load_processed_tweets()
    
    while True:
        try:
            # Check for token refresh
            from token_refresher import check_token_expiry
            if check_token_expiry():
                logger.info("Token expired during mentions monitoring, refreshing...")
                from twitter_agent import get_refreshed_clients
                client, api, _ = get_refreshed_clients()
                logger.info("Clients refreshed in mentions monitoring")
            
            # Get mentions
            logger.info("Checking for new mentions")
            mentions = safe_get_users_mentions(client, user_id, max_results=10)
            
            if mentions and mentions.data:
                logger.info(f"Found {len(mentions.data)} mentions")
                
                # Process each mention
                for mention in mentions.data:
                    # Skip if we've already processed this tweet
                    if mention.id in processed_tweets:
                        logger.debug(f"Skipping already processed mention: {mention.id}")
                        continue
                    
                    # Skip if this is our own tweet
                    if mention.author_id == user_id:
                        logger.debug(f"Skipping our own tweet: {mention.id}")
                        processed_tweets.append(mention.id)
                        continue
                    
                    # Get the full tweet to check if it's a reply to our tweet
                    try:
                        tweet = safe_get_tweet(client, mention.id)
                        is_reply_to_us = False
                        
                        # Check if this is a reply to our tweet
                        if tweet.data.referenced_tweets:
                            for ref_tweet in tweet.data.referenced_tweets:
                                if ref_tweet.type == "replied_to":
                                    # Get the tweet being replied to
                                    parent_tweet = safe_get_tweet(client, ref_tweet.id)
                                    if parent_tweet.data.author_id == user_id:
                                        logger.info(f"Found reply to our tweet: {mention.id}")
                                        is_reply_to_us = True
                        
                        # Add to reply queue
                        logger.info(f"Adding mention {mention.id} to reply queue")
                        reply_queue.put({
                            "tweet_id": mention.id,
                            "user_id": mention.author_id,
                            "text": mention.text,
                            "created_at": mention.created_at,
                            "delay_minutes": 0,  # No delay for mentions
                            "is_reply_to_us": is_reply_to_us
                        })
                        
                        # Mark as processed
                        processed_tweets.append(mention.id)
                        
                    except Exception as e:
                        logger.error(f"Error processing mention {mention.id}: {e}")
                
                # Save processed tweets
                save_processed_tweets(processed_tweets)
                logger.info(f"Saved {len(processed_tweets)} processed tweets")
            else:
                logger.info("No new mentions found")
            
            # Sleep before checking again
            sleep_time = load_monitoring_config().get("check_interval_minutes", 30) * 60
            logger.info(f"Sleeping for {sleep_time/60} minutes before checking mentions again")
            time.sleep(sleep_time)
            
        except tweepy.errors.TooManyRequests as e:
            logger.warning(f"Rate limit exceeded: {e}")
            time.sleep(60 * 15)  # Wait 15 minutes
        except Exception as e:
            logger.error(f"Error in mentions monitoring: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

def monitor_hashtags(client, api):
    """Monitor Twitter for tweets with specific hashtags and add them to the reply queue."""
    logger.info("Starting hashtags monitoring thread")
    
    # Load processed tweets
    processed_tweets = load_processed_tweets()
    
    # Get monitoring configuration
    config = load_monitoring_config()
    delay_minutes = config.get("reply_delay_minutes", 60)
    
    while True:
        try:
            # Check for token refresh
            from token_refresher import check_token_expiry
            if check_token_expiry():
                logger.info("Token expired during hashtags monitoring, refreshing...")
                from twitter_agent import get_refreshed_clients
                client, api, _ = get_refreshed_clients()
                logger.info("Clients refreshed in hashtags monitoring")
            
            # Get the hashtag query
            query = get_hashtag_query()
            logger.info(f"Searching for tweets with hashtags: {query}")
            
            # Search for tweets
            tweets = safe_search_recent_tweets(client, query, max_results=20)
            
            if tweets and tweets.data:
                logger.info(f"Found {len(tweets.data)} tweets with hashtags")
                
                # Get our user ID
                our_user_id = get_user_id(client)
                
                # Process each tweet
                for tweet in tweets.data:
                    # Skip if we've already processed this tweet
                    if tweet.id in processed_tweets:
                        logger.debug(f"Skipping already processed tweet: {tweet.id}")
                        continue
                    
                    # Skip if this is our own tweet
                    if tweet.author_id == our_user_id:
                        logger.debug(f"Skipping our own tweet: {tweet.id}")
                        processed_tweets.append(tweet.id)
                        continue
                    
                    # Add to reply queue with delay
                    logger.info(f"Adding tweet {tweet.id} to reply queue with {delay_minutes} minute delay")
                    reply_queue.put({
                        "tweet_id": tweet.id,
                        "user_id": tweet.author_id,
                        "text": tweet.text,
                        "created_at": tweet.created_at,
                        "delay_minutes": delay_minutes,
                        "is_reply_to_us": False
                    })
                    
                    # Mark as processed
                    processed_tweets.append(tweet.id)
                
                # Save processed tweets
                save_processed_tweets(processed_tweets)
                logger.info(f"Saved {len(processed_tweets)} processed tweets")
            else:
                logger.info("No new tweets with hashtags found")
            
            # Sleep before checking again
            sleep_time = config.get("check_interval_minutes", 30) * 60
            logger.info(f"Sleeping for {sleep_time/60} minutes before checking hashtags again")
            time.sleep(sleep_time)
            
        except tweepy.errors.TooManyRequests as e:
            logger.warning(f"Rate limit exceeded: {e}")
            time.sleep(60 * 15)  # Wait 15 minutes
        except Exception as e:
            logger.error(f"Error in hashtags monitoring: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

def monitor_keywords(client, api):
    """Monitor Twitter for tweets with specific keywords and add them to the reply queue."""
    logger.info("Starting keywords monitoring thread")
    
    # Load processed tweets
    processed_tweets = load_processed_tweets()
    
    # Get monitoring configuration
    config = load_monitoring_config()
    delay_minutes = config.get("reply_delay_minutes", 60)
    
    # Track used categories to rotate through them
    used_categories = []
    
    while True:
        try:
            # Check for token refresh
            from token_refresher import check_token_expiry
            if check_token_expiry():
                logger.info("Token expired during keywords monitoring, refreshing...")
                from twitter_agent import get_refreshed_clients
                client, api, _ = get_refreshed_clients()
                logger.info("Clients refreshed in keywords monitoring")
            
            # Get the keyword query
            query, category = get_keyword_query()
            
            # Track used categories
            if category not in used_categories:
                used_categories.append(category)
                # If we've used all categories, reset the list
                if len(used_categories) >= len(config["keywords"]):
                    used_categories = [category]
            
            logger.info(f"Searching for tweets with keywords from category '{category}': {query}")
            
            # Search for tweets
            tweets = safe_search_recent_tweets(client, query, max_results=20)
            
            if tweets and tweets.data:
                logger.info(f"Found {len(tweets.data)} tweets with keywords")
                
                # Get our user ID
                our_user_id = get_user_id(client)
                
                # Process each tweet
                for tweet in tweets.data:
                    # Skip if we've already processed this tweet
                    if tweet.id in processed_tweets:
                        logger.debug(f"Skipping already processed tweet: {tweet.id}")
                        continue
                    
                    # Skip if this is our own tweet
                    if tweet.author_id == our_user_id:
                        logger.debug(f"Skipping our own tweet: {tweet.id}")
                        processed_tweets.append(tweet.id)
                        continue
                    
                    # Add to reply queue with delay
                    logger.info(f"Adding tweet {tweet.id} to reply queue with {delay_minutes} minute delay")
                    reply_queue.put({
                        "tweet_id": tweet.id,
                        "user_id": tweet.author_id,
                        "text": tweet.text,
                        "created_at": tweet.created_at,
                        "delay_minutes": delay_minutes,
                        "is_reply_to_us": False
                    })
                    
                    # Mark as processed
                    processed_tweets.append(tweet.id)
                
                # Save processed tweets
                save_processed_tweets(processed_tweets)
                logger.info(f"Saved {len(processed_tweets)} processed tweets")
            else:
                logger.info(f"No new tweets with keywords from category '{category}' found")
            
            # Sleep before checking again
            sleep_time = config.get("check_interval_minutes", 30) * 60
            logger.info(f"Sleeping for {sleep_time/60} minutes before checking keywords again")
            time.sleep(sleep_time)
            
        except tweepy.errors.TooManyRequests as e:
            logger.warning(f"Rate limit exceeded: {e}")
            time.sleep(60 * 15)  # Wait 15 minutes
        except Exception as e:
            logger.error(f"Error in keywords monitoring: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

def reply_worker(client, api):
    """Process the reply queue and post replies."""
    logger.info("Starting reply worker thread")
    
    while True:
        try:
            # Check for token refresh
            from token_refresher import check_token_expiry
            if check_token_expiry():
                logger.info("Token expired during reply worker, refreshing...")
                from twitter_agent import get_refreshed_clients
                client, api, _ = get_refreshed_clients()
                logger.info("Clients refreshed in reply worker")
            
            # Check if there are any tweets in the reply queue
            if not reply_queue:
                logger.debug("Reply queue is empty, sleeping for 60 seconds")
                time.sleep(60)
                continue
            
            # Get a tweet from the queue
            tweet_data = reply_queue.get()
            logger.info(f"Processing tweet {tweet_data['tweet_id']} from reply queue")
            
            # Check if we need to delay the reply
            if tweet_data.get("delay_minutes", 0) > 0:
                # Calculate when we should reply
                created_at = tweet_data.get("created_at")
                if created_at:
                    # Convert to datetime if it's a string
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    # Calculate when we should reply
                    reply_after = created_at + timedelta(minutes=tweet_data["delay_minutes"])
                    now = datetime.now(timezone.utc)
                    
                    # If it's not time to reply yet, put it back in the queue
                    if now < reply_after:
                        time_to_wait = (reply_after - now).total_seconds()
                        logger.info(f"Not time to reply to tweet {tweet_data['tweet_id']} yet. Waiting {time_to_wait/60:.1f} more minutes")
                        reply_queue.put(tweet_data)
                        reply_queue.task_done()
                        time.sleep(5)  # Sleep a bit before checking the next item
                        continue
            
            # Generate a reply using AI
            try:
                # Get the tweet text
                tweet_text = tweet_data["text"]
                logger.info(f"Generating reply to: {tweet_text}")
                
                # Generate the reply
                from ai_utils import generate_reply
                reply_text = generate_reply(tweet_text)
                logger.info(f"Generated reply: {reply_text}")
                
                # Post the reply
                if tweet_data.get("is_reply_to_us", False):
                    # This is a reply to our tweet, we can always reply to it
                    logger.info(f"Replying to a comment on our tweet {tweet_data['tweet_id']}")
                    response = safe_create_tweet(client, reply_text, in_reply_to_tweet_id=tweet_data["tweet_id"])
                    logger.info(f"Posted reply to tweet {tweet_data['tweet_id']}: {reply_text}")
                else:
                    # For other tweets, we'll try to reply directly
                    # Twitter will handle permissions on their end
                    try:
                        logger.info(f"Attempting to reply to tweet {tweet_data['tweet_id']}")
                        response = safe_create_tweet(client, reply_text, in_reply_to_tweet_id=tweet_data["tweet_id"])
                        logger.info(f"Successfully posted reply to tweet {tweet_data['tweet_id']}")
                    except tweepy.errors.Forbidden as e:
                        logger.warning(f"Permission error posting reply to {tweet_data['tweet_id']}: {e}")
                        # This user has restricted who can reply to their tweets
                        # We could try to follow them first and then reply, but that might be too aggressive
                        logger.info("Skipping this tweet due to reply restrictions")
                    except tweepy.errors.TooManyRequests as e:
                        logger.warning(f"Rate limit exceeded when replying to {tweet_data['tweet_id']}: {e}")
                        # Put the tweet back in the queue to try again later
                        reply_queue.put(tweet_data)
                        # Sleep for a while to respect rate limits
                        time.sleep(60 * 15)  # 15 minutes
                    except Exception as e:
                        logger.error(f"Unexpected error posting reply to {tweet_data['tweet_id']}: {e}")
                
            except Exception as e:
                logger.error(f"Error processing reply for tweet {tweet_data['tweet_id']}: {e}")
            
            # Mark the task as done
            reply_queue.task_done()
            logger.info(f"Completed processing tweet {tweet_data['tweet_id']}")
            
            # Sleep a bit to avoid rate limits
            time.sleep(random.uniform(5, 15))
            
        except Exception as e:
            logger.error(f"Error in reply worker: {e}")
            time.sleep(30)  # Wait before retrying

def get_user_id(client):
    """Get the user ID of the authenticated user."""
    try:
        user = client.get_me()
        return user.data.id
    except Exception as e:
        logger.error(f"Error getting user ID: {e}")
        raise

def main():
    """Run the Twitter monitoring system."""
    logger.info("Starting Twitter monitoring system")
    
    try:
        # Load credentials
        credentials = load_config()
        
        # Initialize Twitter clients
        client, api = initialize_twitter_client(credentials)
        
        # Get the user ID
        user_id = get_user_id(client)
        logger.info(f"Authenticated as user ID: {user_id}")
        
        # Create threads for monitoring
        mention_thread = threading.Thread(target=monitor_mentions, args=(client, api, user_id))
        hashtag_thread = threading.Thread(target=monitor_hashtags, args=(client, api))
        keyword_thread = threading.Thread(target=monitor_keywords, args=(client, api))
        reply_thread = threading.Thread(target=reply_worker, args=(client, api))
        
        # Start the threads
        mention_thread.daemon = True
        hashtag_thread.daemon = True
        keyword_thread.daemon = True
        reply_thread.daemon = True
        
        mention_thread.start()
        hashtag_thread.start()
        keyword_thread.start()
        reply_thread.start()
        
        logger.info("All monitoring threads started")
        
        # Keep the main thread alive
        while True:
            time.sleep(60)
            
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        return 1
    
    return 0

def test_reply_queue(client):
    """Add a test tweet to the reply queue for debugging."""
    logger.info("Adding test tweet to reply queue")
    reply_queue.put({
        "tweet_id": "1234567890",  # This is a dummy ID
        "user_id": "987654321",    # This is a dummy ID
        "text": "@DrAlexAI I've been so tired lately, no matter how much I sleep. What's wrong with me?",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "delay_minutes": 0,        # Reply immediately
        "is_reply_to_us": False
    })
    logger.info("Test tweet added to reply queue")

if __name__ == "__main__":
    main() 