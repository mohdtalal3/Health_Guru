import tweepy
import json
import logging
from ai_utils import generate_reply
from twitter_poster import load_config, initialize_twitter_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simple_mention_reply.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("simple_mention_reply")

def reply_to_mentions():
    """Simple function to check for mentions and reply to them."""
    # Load credentials and initialize clients
    credentials = load_config()
    client, api = initialize_twitter_client(credentials)
    
    # Get the user ID
    me = client.get_me()
    my_user_id = me.data.id
    logger.info(f"Checking mentions for user ID: {my_user_id}")
    
    # Keep track of processed mentions
    processed_mentions = set()
    
    # Try to load previously processed mentions from file
    try:
        with open("processed_mentions.json", "r") as f:
            processed_mentions = set(json.load(f))
        logger.info(f"Loaded {len(processed_mentions)} previously processed mentions")
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info("No previously processed mentions found")
    
    # Retrieve the latest mentions
    mentions_response = client.get_users_mentions(
        id=my_user_id,
        max_results=10,
        tweet_fields=["author_id", "created_at", "conversation_id"]
    )
    
    if mentions_response.data:
        logger.info(f"Found {len(mentions_response.data)} mentions")
        
        for mention in mentions_response.data:
            # Skip if already processed
            if str(mention.id) in processed_mentions:
                logger.info(f"Skipping already processed mention: {mention.id}")
                continue
            
            logger.info(f"Processing mention: {mention.id} - {mention.text}")
            
            # Check if this is a reply to our tweet
            is_reply_to_us = False
            try:
                tweet = client.get_tweet(mention.conversation_id)
                if tweet.data.author_id == my_user_id:
                    is_reply_to_us = True
                    logger.info(f"Mention {mention.id} is a reply to our tweet")
            except Exception as e:
                logger.warning(f"Error checking if tweet is reply to us: {e}")
            
            # Generate a reply
            try:
                reply_text = generate_reply(mention.text)
                logger.info(f"Generated reply: {reply_text}")
                
                # Post the reply
                response = client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=mention.id
                )
                logger.info(f"Posted reply to {mention.id}: {reply_text}")
                
                # Mark as processed
                processed_mentions.add(str(mention.id))
                
            except Exception as e:
                logger.error(f"Error replying to mention {mention.id}: {e}")
        
        # Save processed mentions to file
        with open("processed_mentions.json", "w") as f:
            json.dump(list(processed_mentions), f)
        
    else:
        logger.info("No mentions found")

if __name__ == "__main__":
    logger.info("Starting simple mention reply script")
    reply_to_mentions()
    logger.info("Finished simple mention reply script") 