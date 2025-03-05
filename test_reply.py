import logging
import datetime
import time
from twitter_poster import load_config, initialize_twitter_client
from ai_utils import generate_reply
from twitter_monitor import safe_create_tweet

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_reply.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_reply")

def test_generate_reply():
    """Test the generate_reply function."""
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

def test_post_reply():
    """Test posting a reply to Twitter."""
    # Load credentials and initialize clients
    credentials = load_config()
    client, api = initialize_twitter_client(credentials)
    
    # Generate a test reply
    test_tweet = "@DrAlexAI I've been so tired lately, no matter how much I sleep. What's wrong with me?"
    reply = generate_reply(test_tweet)
    
    logger.info(f"Generated reply: {reply}")
    
    # Uncomment to actually post to Twitter (be careful!)
    # tweet_id = input("Enter a tweet ID to reply to: ")
    # if tweet_id:
    #     try:
    #         response = safe_create_tweet(client, reply, in_reply_to_tweet_id=tweet_id)
    #         logger.info(f"Posted reply: {response}")
    #     except Exception as e:
    #         logger.error(f"Error posting reply: {e}")

if __name__ == "__main__":
    logger.info("Starting reply tests")
    
    # Test reply generation
    test_generate_reply()
    
    # Test posting a reply (commented out by default)
    # test_post_reply()
    
    logger.info("Reply tests completed") 