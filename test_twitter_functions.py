import tweepy
import json
import time
import datetime
import logging
import sys
import os
from ai_utils import generate_reply, generate_tweet_only, generate_tweet_and_image
from twitter_poster import load_config, initialize_twitter_client, post_tweet_without_image
from twitter_monitor import (
    load_monitoring_config, 
    get_hashtag_query, 
    get_keyword_query,
    safe_get_users_mentions,
    safe_get_tweet,
    safe_search_recent_tweets,
    safe_create_tweet,
    safe_get_friendship,
    get_user_id
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_functions.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_functions")

# Initialize global variables
client = None
api = None
user_id = None
processed_tweets = set()

def setup():
    """Initialize the Twitter clients."""
    global client, api, user_id
    
    logger.info("Setting up Twitter clients...")
    credentials = load_config()
    client, api = initialize_twitter_client(credentials)
    user_id = get_user_id(client)
    logger.info(f"Setup complete. User ID: {user_id}")
    return client, api, user_id

def test_ai_functions():
    """Test the AI functions for generating tweets and replies."""
    logger.info("\n=== TESTING AI FUNCTIONS ===")
    
    # Test generate_tweet_only
    logger.info("Testing generate_tweet_only...")
    try:
        tweet = generate_tweet_only()
        logger.info(f"Generated tweet: {tweet}")
    except Exception as e:
        logger.error(f"Error generating tweet: {e}")
    
    # Test generate_reply
    logger.info("Testing generate_reply...")
    test_tweets = [
        "@DrAlexAI I've been so tired lately, no matter how much I sleep. What's wrong with me?",
        "@DrAlexAI Is it normal to have headaches every day?",
        "@DrAlexAI What's the best way to improve gut health?"
    ]
    
    for tweet in test_tweets:
        logger.info(f"Testing reply generation for: {tweet}")
        try:
            reply = generate_reply(tweet)
            logger.info(f"Generated reply: {reply}")
        except Exception as e:
            logger.error(f"Error generating reply: {e}")
    
    # Test generate_tweet_and_image (optional - takes longer)
    logger.info("Testing generate_tweet_and_image... (this may take a while)")
    try:
        result = generate_tweet_and_image()
        logger.info(f"Generated tweet with image: {result['tweet']}")
        logger.info(f"Image saved at: {result['image_path']}")
    except Exception as e:
        logger.error(f"Error generating tweet with image: {e}")

def test_monitoring_config():
    """Test loading the monitoring configuration."""
    logger.info("\n=== TESTING MONITORING CONFIG ===")
    
    try:
        config = load_monitoring_config()
        logger.info(f"Loaded monitoring config: {json.dumps(config, indent=2)}")
        
        hashtag_query = get_hashtag_query()
        logger.info(f"Hashtag query: {hashtag_query}")
        
        keyword_query = get_keyword_query()
        logger.info(f"Keyword query: {keyword_query}")
    except Exception as e:
        logger.error(f"Error loading monitoring config: {e}")

def test_mentions_monitoring():
    """Test the mentions monitoring functionality."""
    logger.info("\n=== TESTING MENTIONS MONITORING ===")
    
    try:
        mentions = safe_get_users_mentions(client, user_id)
        
        if mentions.data:
            logger.info(f"Found {len(mentions.data)} mentions")
            for mention in mentions.data:
                logger.info(f"Mention: {mention.id} - {mention.text}")
                
                # Check if this is a reply to our tweet
                is_reply_to_us = False
                try:
                    tweet = safe_get_tweet(client, mention.conversation_id)
                    if tweet.data.author_id == user_id:
                        is_reply_to_us = True
                        logger.info(f"Mention {mention.id} is a reply to our tweet")
                except Exception as e:
                    logger.warning(f"Error checking if tweet is reply to us: {e}")
                
                # Process this mention (without adding to queue)
                if mention.id not in processed_tweets:
                    logger.info(f"Processing new mention: {mention.id}")
                    
                    # Generate a reply
                    reply_text = generate_reply(mention.text)
                    logger.info(f"Generated reply: {reply_text}")
                    
                    # Don't actually post the reply unless explicitly requested
                    if len(sys.argv) > 1 :#and sys.argv[1] == "--post-replies":
                        try:
                            response = safe_create_tweet(client, reply_text, in_reply_to_tweet_id=mention.id)
                            logger.info(f"Posted reply to {mention.id}: {reply_text}")
                        except Exception as e:
                            logger.error(f"Error posting reply: {e}")
                    else:
                        logger.info("Skipping posting reply (use --post-replies to enable)")
                    
                    processed_tweets.add(mention.id)
                else:
                    logger.info(f"Mention {mention.id} already processed")
        else:
            logger.info("No mentions found")
    except Exception as e:
        logger.error(f"Error in mentions monitoring: {e}")

def test_hashtags_monitoring():
    """Test the hashtags monitoring functionality."""
    logger.info("\n=== TESTING HASHTAGS MONITORING ===")
    
    try:
        # Get the hashtag query
        query = get_hashtag_query()
        logger.info(f"Searching for hashtags with query: {query}")
        
        # Search for tweets with the hashtags
        tweets = safe_search_recent_tweets(client, query)
        
        if tweets.data:
            logger.info(f"Found {len(tweets.data)} tweets with hashtags")
            for tweet in tweets.data:
                logger.info(f"Tweet: {tweet.id} - {tweet.text}")
                
                # Process this tweet (without adding to queue)
                if tweet.id not in processed_tweets:
                    logger.info(f"Processing new hashtag tweet: {tweet.id}")
                    
                    # Generate a reply
                    reply_text = generate_reply(tweet.text)
                    logger.info(f"Generated reply: {reply_text}")
                    
                    # Don't actually post the reply unless explicitly requested
                    if len(sys.argv) > 1 and sys.argv[1] == "--post-replies":
                        try:
                            # Check if user follows us
                            friendship = safe_get_friendship(api, user_id, tweet.author_id)
                            if friendship[0].followed_by:
                                response = safe_create_tweet(client, reply_text, in_reply_to_tweet_id=tweet.id)
                                logger.info(f"Posted reply to {tweet.id}: {reply_text}")
                            else:
                                logger.info(f"Skipping reply to {tweet.id} - user doesn't follow us")
                        except Exception as e:
                            logger.error(f"Error posting reply: {e}")
                    else:
                        logger.info("Skipping posting reply (use --post-replies to enable)")
                    
                    processed_tweets.add(tweet.id)
                else:
                    logger.info(f"Hashtag tweet {tweet.id} already processed")
        else:
            logger.info("No tweets with hashtags found")
    except Exception as e:
        logger.error(f"Error in hashtags monitoring: {e}")

def test_keywords_monitoring():
    """Test the keywords monitoring functionality."""
    logger.info("\n=== TESTING KEYWORDS MONITORING ===")
    
    try:
        # Get the keyword query
        query = get_keyword_query()
        logger.info(f"Searching for keywords with query: {query}")
        
        # Search for tweets with the keywords
        tweets = safe_search_recent_tweets(client, query)
        
        if tweets.data:
            logger.info(f"Found {len(tweets.data)} tweets with keywords")
            for tweet in tweets.data:
                logger.info(f"Tweet: {tweet.id} - {tweet.text}")
                
                # Process this tweet (without adding to queue)
                if tweet.id not in processed_tweets:
                    logger.info(f"Processing new keyword tweet: {tweet.id}")
                    
                    # Generate a reply
                    reply_text = generate_reply(tweet.text)
                    logger.info(f"Generated reply: {reply_text}")
                    
                    # Don't actually post the reply unless explicitly requested
                    if len(sys.argv) > 1 and sys.argv[1] == "--post-replies":
                        try:
                            # Check if user follows us
                            friendship = safe_get_friendship(api, user_id, tweet.author_id)
                            if friendship[0].followed_by:
                                response = safe_create_tweet(client, reply_text, in_reply_to_tweet_id=tweet.id)
                                logger.info(f"Posted reply to {tweet.id}: {reply_text}")
                            else:
                                logger.info(f"Skipping reply to {tweet.id} - user doesn't follow us")
                        except Exception as e:
                            logger.error(f"Error posting reply: {e}")
                    else:
                        logger.info("Skipping posting reply (use --post-replies to enable)")
                    
                    processed_tweets.add(tweet.id)
                else:
                    logger.info(f"Keyword tweet {tweet.id} already processed")
        else:
            logger.info("No tweets with keywords found")
    except Exception as e:
        logger.error(f"Error in keywords monitoring: {e}")

def test_post_tweet():
    """Test posting a tweet."""
    logger.info("\n=== TESTING TWEET POSTING ===")
    
    # Only post if explicitly requested
    if len(sys.argv) > 1 and sys.argv[1] == "--post-tweet":
        try:
            tweet_text = generate_tweet_only()
            logger.info(f"Generated tweet: {tweet_text}")
            
            response = post_tweet_without_image(client, tweet_text)
            logger.info(f"Posted tweet: {response}")
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
    else:
        logger.info("Skipping posting tweet (use --post-tweet to enable)")
        tweet_text = generate_tweet_only()
        logger.info(f"Generated tweet (not posted): {tweet_text}")

def test_specific_reply():
    """Test replying to a specific tweet ID."""
    logger.info("\n=== TESTING SPECIFIC REPLY ===")
    
    if len(sys.argv) > 2 and sys.argv[1] == "--reply-to":
        tweet_id = sys.argv[2]
        try:
            # Get the tweet
            tweet = safe_get_tweet(client, tweet_id)
            if tweet.data:
                logger.info(f"Found tweet: {tweet.data.id} - {tweet.data.text}")
                
                # Generate a reply
                reply_text = generate_reply(tweet.data.text)
                logger.info(f"Generated reply: {reply_text}")
                
                # Post the reply
                response = safe_create_tweet(client, reply_text, in_reply_to_tweet_id=tweet_id)
                logger.info(f"Posted reply to {tweet_id}: {reply_text}")
            else:
                logger.error(f"Tweet {tweet_id} not found")
        except Exception as e:
            logger.error(f"Error replying to tweet {tweet_id}: {e}")
    else:
        logger.info("Skipping specific reply (use --reply-to <tweet_id> to enable)")

def test_specific_mention(mention_id):
    """Test replying to a specific mention ID."""
    logger.info(f"\n=== TESTING SPECIFIC MENTION ID: {mention_id} ===")
    
    try:
        # Get the tweet
        tweet = safe_get_tweet(client, mention_id)
        if tweet.data:
            logger.info(f"Found mention: {tweet.data.id} - {tweet.data.text}")
            
            # Generate a reply
            reply_text = generate_reply(tweet.data.text)
            logger.info(f"Generated reply: {reply_text}")
            
            # Post the reply
            response = safe_create_tweet(client, reply_text, in_reply_to_tweet_id=mention_id)
            logger.info(f"Posted reply to mention {mention_id}: {reply_text}")
        else:
            logger.error(f"Mention {mention_id} not found")
    except Exception as e:
        logger.error(f"Error replying to mention {mention_id}: {e}")

def main():
    """Run all tests."""
    logger.info("Starting Twitter function tests")
    
    # Setup Twitter clients
    global client, api, user_id
    client, api, user_id = setup()
    
    # Run tests based on command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--ai-only":
            test_ai_functions()
        elif sys.argv[1] == "--config-only":
            test_monitoring_config()
        elif sys.argv[1] == "--mentions-only":
            test_mentions_monitoring()
        elif sys.argv[1] == "--hashtags-only":
            test_hashtags_monitoring()
        elif sys.argv[1] == "--keywords-only":
            test_keywords_monitoring()
        elif sys.argv[1] == "--post-tweet":
            test_post_tweet()
        elif sys.argv[1] == "--reply-to" and len(sys.argv) > 2:
            test_specific_reply()
        elif sys.argv[1] == "--reply-to-mention" and len(sys.argv) > 2:
            test_specific_mention(sys.argv[2])
        else:
            print("Available test options:")
            print("  --ai-only: Test AI functions only")
            print("  --config-only: Test monitoring config only")
            print("  --mentions-only: Test mentions monitoring only")
            print("  --hashtags-only: Test hashtags monitoring only")
            print("  --keywords-only: Test keywords monitoring only")
            print("  --post-tweet: Test posting a tweet")
            print("  --post-replies: Enable posting replies in monitoring tests")
            print("  --reply-to <tweet_id>: Test replying to a specific tweet")
            print("  --reply-to-mention <mention_id>: Test replying to a specific mention")
    else:
        # Run all tests
        test_ai_functions()
        test_monitoring_config()
        test_mentions_monitoring()
        test_hashtags_monitoring()
        test_keywords_monitoring()
        test_post_tweet()
    
    logger.info("All tests completed")

if __name__ == "__main__":
    main() 