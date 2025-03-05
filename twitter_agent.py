import logging
import threading
import time
import argparse
import os
from twitter_poster import post_random_tweet
from twitter_monitor import (
    load_config, 
    initialize_twitter_client, 
    get_user_id,
    load_processed_tweets,
    save_processed_tweets,
    monitor_mentions,
    monitor_hashtags,
    monitor_keywords,
    reply_worker,
    test_reply_queue
)
from token_refresher import load_tokens, save_tokens, refresh_access_token, check_token_expiry

# Set up logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("twitter_agent.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("twitter_agent")

def check_and_refresh_tokens():
    """Check if bearer tokens need refreshing and refresh them if needed."""
    logger.info("Checking if bearer tokens need refreshing")
    
    try:
        # Check if tokens need refreshing
        if check_token_expiry():
            logger.info("Bearer tokens need refreshing")
            
            # Load tokens to get credentials
            tokens = load_tokens()
            
            if not tokens:
                logger.error("No tokens found, cannot refresh")
                return False
            
            # Refresh the bearer tokens
            refreshed_tokens = refresh_access_token(
                tokens.get("client_id"),
                tokens.get("client_id_secret"),
                tokens.get("refresh_token")
            )
            
            if refreshed_tokens:
                logger.info("Bearer tokens refreshed successfully")
                return True
            else:
                logger.error("Failed to refresh bearer tokens")
                return False
        else:
            logger.info("Bearer tokens are still valid, no refresh needed")
            return False
            
    except Exception as e:
        logger.error(f"Error checking/refreshing bearer tokens: {e}")
        return False

def get_refreshed_clients():
    """Get fresh API clients, refreshing bearer tokens if necessary."""
    # Check and refresh bearer tokens if needed
    tokens_refreshed = check_and_refresh_tokens()
    
    # Load credentials
    credentials = load_config()
    
    # Initialize clients with fresh bearer tokens
    client, api = initialize_twitter_client(credentials)
    
    return client, api, tokens_refreshed

def run_tweet_scheduler(client, api, interval_hours=8):
    """Thread function to post tweets at regular intervals."""
    logger.info(f"Starting tweet scheduler (interval: {interval_hours} hours)")
    
    while True:
        try:
            # Check if tokens need refreshing
            client, api, tokens_refreshed = get_refreshed_clients()
            
            # Post a random tweet
            logger.info("Posting a random tweet...")
            post_random_tweet()
            logger.info("Tweet posted successfully")
            
            # Sleep for the specified interval
            sleep_time = interval_hours * 60 * 60  # Convert hours to seconds
            logger.info(f"Sleeping for {interval_hours} hours before posting next tweet")
            time.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"Error in tweet scheduler: {e}")
            # Sleep for 15 minutes before retrying
            logger.info("Sleeping for 15 minutes before retrying")
            time.sleep(15 * 60)

def token_refresh_monitor():
    """Thread to periodically check and refresh tokens."""
    logger.info("Starting token refresh monitor thread")
    
    while True:
        try:
            # Check and refresh tokens if needed
            check_and_refresh_tokens()
            
            # Sleep for 30 minutes before checking again
            logger.info("Token monitor sleeping for 30 minutes")
            time.sleep(30 * 60)
            
        except Exception as e:
            logger.error(f"Error in token refresh monitor: {e}")
            time.sleep(5 * 60)  # Sleep for 5 minutes before retrying

def start_monitoring_system(include_scheduler=True, test_mode=False, scheduler_interval=8):
    """Start the Twitter monitoring and posting system."""
    logger.info("Starting Twitter agent system")
    
    # Get fresh clients
    client, api, _ = get_refreshed_clients()
    
    # Load previously processed tweets
    load_processed_tweets()
    
    # Get the user ID for monitoring mentions
    user_id = get_user_id(client)
    logger.info(f"Starting monitoring for user ID: {user_id}")
    
    # Start the monitoring threads
    threads = []
    
    # Thread for token refresh monitoring
    token_thread = threading.Thread(
        target=token_refresh_monitor,
        daemon=True,
        name="TokenRefreshMonitor"
    )
    threads.append(token_thread)
    
    # Thread for monitoring mentions
    mentions_thread = threading.Thread(
        target=monitor_mentions,
        args=(client, api, user_id),
        daemon=True,
        name="MentionsMonitor"
    )
    threads.append(mentions_thread)
    
    # Thread for monitoring hashtags
    hashtags_thread = threading.Thread(
        target=monitor_hashtags,
        args=(client, api),
        daemon=True,
        name="HashtagsMonitor"
    )
    threads.append(hashtags_thread)
    
    # Thread for monitoring keywords
    keywords_thread = threading.Thread(
        target=monitor_keywords,
        args=(client, api),
        daemon=True,
        name="KeywordsMonitor"
    )
    threads.append(keywords_thread)
    
    # Thread for processing replies
    reply_thread = threading.Thread(
        target=reply_worker,
        args=(client, api),
        daemon=True,
        name="ReplyWorker"
    )
    threads.append(reply_thread)
    
    # Thread for posting scheduled tweets (optional)
    if include_scheduler:
        scheduler_thread = threading.Thread(
            target=run_tweet_scheduler,
            args=(client, api, scheduler_interval),
            daemon=True,
            name="TweetScheduler"
        )
        threads.append(scheduler_thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
        logger.info(f"Started thread: {thread.name}")
    
    logger.info("All threads started")
    
    # Add a test tweet to the reply queue if in test mode
    if test_mode:
        logger.info("Running in test mode, adding test tweet to reply queue")
        test_reply_queue(client)
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        # Save processed tweets before exiting
        save_processed_tweets()

def main():
    """Parse command line arguments and start the system."""
    parser = argparse.ArgumentParser(description="Twitter AI Agent")
    parser.add_argument("--monitor-only", action="store_true", help="Run only the monitoring system without tweet scheduler")
    parser.add_argument("--scheduler-only", action="store_true", help="Run only the tweet scheduler")
    parser.add_argument("--post-now", action="store_true", help="Post a tweet immediately and exit")
    parser.add_argument("--test", action="store_true", help="Run in test mode (adds a test tweet to the reply queue)")
    parser.add_argument("--interval", type=int, default=8, help="Hours between scheduled tweets (default: 8)")
    parser.add_argument("--refresh-tokens", action="store_true", help="Force refresh of tokens and exit")
    
    args = parser.parse_args()
    
    if args.refresh_tokens:
        # Just refresh tokens and exit
        logger.info("Forcing token refresh and exiting")
        check_and_refresh_tokens()
        return
    
    if args.post_now:
        # Just post a single tweet and exit
        logger.info("Posting a single tweet and exiting")
        # Refresh tokens if needed
        client, api, _ = get_refreshed_clients()
        post_random_tweet()
        return
    
    if args.scheduler_only:
        # Run only the tweet scheduler
        logger.info("Running tweet scheduler only")
        # Refresh tokens if needed
        client, api, _ = get_refreshed_clients()
        
        # Start token refresh monitor
        token_thread = threading.Thread(
            target=token_refresh_monitor,
            daemon=True,
            name="TokenRefreshMonitor"
        )
        token_thread.start()
        
        scheduler_thread = threading.Thread(
            target=run_tweet_scheduler,
            args=(client, api, args.interval),
            daemon=False  # Non-daemon so it keeps running
        )
        scheduler_thread.start()
        try:
            scheduler_thread.join()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        return
    
    # Run the full system or monitoring-only
    include_scheduler = not args.monitor_only
    start_monitoring_system(
        include_scheduler=include_scheduler,
        test_mode=args.test,
        scheduler_interval=args.interval
    )

if __name__ == "__main__":
    main() 