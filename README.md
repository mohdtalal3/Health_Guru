# Twitter AI Agent

This project automatically generates and posts tweets with or without images to Twitter using AI-generated content. It also monitors Twitter for mentions, hashtags, and keywords to automatically reply to relevant tweets.

## Features

- Generate tweets with AI using OpenAI's GPT models
- Generate images with AI using DALL-E
- Post tweets with or without images based on a configurable probability ratio
- Schedule tweets to be posted at specific times
- Monitor Twitter for mentions and automatically reply
- Monitor specific hashtags and keywords related to health
- Reply to relevant tweets with helpful information
- Multi-threaded architecture for efficient operation

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your environment variables in a `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```
4. Make sure your Twitter API credentials are correctly set in `config.json`

## Usage

### Run the Complete System

To run the complete system with both tweet posting and monitoring:

```bash
python twitter_agent.py
```

This will start:
- The tweet scheduler for posting regular tweets (every 8 hours by default)
- The Twitter monitor for replying to mentions, hashtags, and keywords

### Command-Line Options

The system supports several command-line options:

```bash
python twitter_agent.py --monitor-only  # Run only the monitoring system without tweet scheduler
python twitter_agent.py --scheduler-only  # Run only the tweet scheduler
python twitter_agent.py --post-now  # Post a tweet immediately and exit
python twitter_agent.py --test  # Run in test mode (adds a test tweet to the reply queue)
python twitter_agent.py --interval 4  # Set hours between scheduled tweets (default: 8)
python twitter_agent.py --refresh-tokens  # Force refresh of Twitter API tokens and exit
```

You can also refresh tokens directly using:

```bash
python token_refresher.py --force  # Force refresh tokens even if not expired
```

### Post a Single Tweet

To post a single tweet immediately:

```bash
python twitter_agent.py --post-now
```

### Run Only the Monitoring System

To run only the Twitter monitoring and auto-reply system without posting scheduled tweets:

```bash
python twitter_agent.py --monitor-only
```

### Run Only the Tweet Scheduler

To run only the tweet scheduler without the monitoring system:

```bash
python twitter_agent.py --scheduler-only
```

### Testing the System

To test the system by adding a test tweet to the reply queue:

```bash
python twitter_agent.py --test
```

For more granular testing of individual components, use the test script:

```bash
python test_twitter_functions.py --mentions-only  # Test mentions monitoring only
python test_twitter_functions.py --hashtags-only  # Test hashtags monitoring only
python test_twitter_functions.py --keywords-only  # Test keywords monitoring only
python test_twitter_functions.py --ai-only  # Test AI functions only
python test_twitter_functions.py --reply-to-mention <mention_id>  # Test replying to a specific mention
```

## Customizing Content

### Tweet and Image Content

The content of the tweets and images is determined by the templates in `prompts_template_alex.json`. You can modify these templates to change the style and content of the generated tweets and images.

### Monitoring Configuration

The monitoring system is configured in the `monitoring` section of `prompts_template_alex.json`:

- `hashtags`: List of hashtags to monitor
- `keywords`: Categories of keywords to monitor
  - The system selects one random category per check to avoid query length limits
  - Each category contains related keywords (e.g., "pain", "respiratory", "digestive")
  - You can add or modify categories and keywords to match your needs
- `check_interval_minutes`: How often to check for new tweets (default: 30 minutes)
- `reply_delay_minutes`: How long to wait before replying to hashtag/keyword matches (default: 60 minutes)

## Adjusting the Image Probability

You can adjust the probability of posting tweets with images by changing the `image_probability` parameter in `post_random_tweet()`. A value of 0.7 means 70% of tweets will include an image.

## Time Intervals and Scheduling

The system uses various time intervals for different operations. Here's a breakdown of the default intervals and how to adjust them:

### Tweet Scheduler Intervals

- **Default posting interval**: 8 hours
- **How to change**: Use the `--interval` command-line option
  ```bash
  python twitter_agent.py --interval 4  # Post tweets every 4 hours
  ```
- **Configuration in code**: Modify the `interval_hours` parameter in `run_tweet_scheduler()`

### Monitoring Intervals

- **Mentions, hashtags, and keywords check interval**: 30 minutes
  - **How to change**: Edit the `check_interval_minutes` value in the `monitoring` section of `prompts_template_alex.json`
  - **Effect**: Controls how often the system checks for new tweets to reply to

- **Reply delay for hashtags and keywords**: 60 minutes
  - **How to change**: Edit the `reply_delay_minutes` value in the `monitoring` section of `prompts_template_alex.json`
  - **Effect**: Controls how long the system waits before replying to hashtag/keyword matches
  - **Note**: Mentions are always replied to immediately (no delay)

### Token Refresh Intervals

- **Token refresh check interval**: 30 minutes
  - **How to change**: Modify the sleep time in `token_refresh_monitor()` in `twitter_agent.py`
  - **Effect**: Controls how often the system checks if tokens need refreshing

- **Token refresh threshold**: 5 minutes before expiration
  - **How to change**: Modify the threshold in `check_token_expiry()` in `token_refresher.py`
  - **Effect**: Controls how early before expiration the system refreshes tokens

### Rate Limiting and Retry Intervals

- **Rate limit retry delay**: Exponential backoff (4-60 seconds)
  - **How to change**: Modify the `wait_exponential` parameters in the `twitter_retry` decorator
  - **Effect**: Controls how long the system waits between retry attempts for rate-limited API calls

- **Error retry delay**: 60 seconds
  - **How to change**: Modify the sleep time in the exception handlers in monitoring functions
  - **Effect**: Controls how long the system waits before retrying after encountering an error

## Token Management

The system includes automatic token refreshing to handle Twitter API token expiration:

- Tokens are stored in `tokens.json` and automatically refreshed when needed
- A dedicated token refresh monitor runs in the background to check token validity
- Each monitoring thread checks token expiry before making API calls
- You can force a token refresh with `python twitter_agent.py --refresh-tokens`

## Files

- `twitter_agent.py`: Main script with command-line interface to run the system
- `twitter_poster.py`: Module for posting tweets with or without images
- `twitter_monitor.py`: Module for monitoring Twitter and auto-replying
- `ai_utils.py`: Utilities for generating tweets, images, and replies using AI
- `token_refresher.py`: Handles refreshing Twitter API tokens when they expire
- `test_twitter_functions.py`: Script for testing individual components
- `simple_mention_reply.py`: Simple script for replying to mentions without threading
- `prompts_template_alex.json`: Templates for generating content and monitoring configuration
- `config.json`: Twitter API credentials
- `tokens.json`: Stores refreshed Twitter API tokens
- `processed_tweets.json`: Keeps track of tweets that have been processed

## Requirements

- Python 3.7+
- Tweepy 4.14.0+
- OpenAI API
- Python-dotenv
- Pillow
- Requests
- Schedule
- Tenacity 

## Configuration Files and Environment Variables

### Configuration Files

The system uses several configuration files:

1. **`config.json`**: Contains Twitter API credentials
   ```json
   {
       "twitter": {
           "consumer_key": "YOUR_CONSUMER_KEY",
           "consumer_secret": "YOUR_CONSUMER_SECRET",
           "access_token": "YOUR_ACCESS_TOKEN",
           "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET",
           "bearer_token": "YOUR_BEARER_TOKEN"
       },
       "openai": {
           "api_key": "YOUR_OPENAI_API_KEY"
       }
   }
   ```

2. **`prompts_template_alex.json`**: Contains templates for tweets, images, and monitoring configuration
   - `Image_prompts`: Templates for generating tweets with images
   - `tweet_prompt`: Templates for generating text-only tweets
   - `reply_prompt`: Template for generating replies to tweets
   - `monitoring`: Configuration for hashtags, keywords, and intervals

3. **`tokens.json`**: Automatically generated file that stores refreshed Twitter API tokens
   - This file is managed by the token refresher and should not be edited manually

4. **`processed_tweets.json`**: Automatically generated file that keeps track of processed tweets
   - This file ensures the system doesn't process the same tweets multiple times

### Environment Variables

You can use environment variables instead of or in addition to the configuration files:

1. Create a `.env` file in the project root directory:
   ```
   OPENAI_API_KEY=your_openai_api_key
   TWITTER_CONSUMER_KEY=your_consumer_key
   TWITTER_CONSUMER_SECRET=your_consumer_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
   TWITTER_BEARER_TOKEN=your_bearer_token
   ```

2. The system will first check for environment variables, then fall back to the configuration files

### Logging Configuration

The system uses Python's logging module with the following configuration:

- Log files are stored with UTF-8 encoding to properly handle emojis and special characters
- Each component has its own log file (e.g., `twitter_agent.log`, `token_refresher.log`)
- Log level is set to INFO by default
- Logs include timestamps, component names, and log levels

To change the logging configuration, modify the `logging.basicConfig()` calls in each file. 