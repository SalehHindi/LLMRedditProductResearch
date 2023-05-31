import praw
import csv
from praw.models import MoreComments
from datetime import datetime
import time

from serpapi import GoogleSearch

import promptlayer
openai = promptlayer.openai

################################################
## Description
################################################
# This program helps do product research by searching for 
# relevant reddit threads, parsing the comments, and
# applying tagging + sentiment analysis on each of the comments
# Flexible enough to add your own prompts to add other comment tagging features.

################################################
## Docs
################################################
# https://praw.readthedocs.io/en/latest/getting_started/quick_start.html
# https://serpapi.com/search-api

################################################
## Secrets
################################################
SERP_API_KEY = ""

PL_KEY = ""
OPENAI_KEY = ""

REDDIT_USERNAME = ""
REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""
################################################


promptlayer.api_key = PL_KEY
openai.api_key = OPENAI_KEY

def call_inference(model, prompt, pl_tags):
    # models = 'gpt-4', 'gpt-3.5-turbo'
    
    # Self rate limit 
    time.sleep(2)
    
    messages = [{'role': 'user', 'content': prompt}]
    completion = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        # stream=True,
        pl_tags=pl_tags,
        temperature=0,
        max_tokens=2048,
    )

    content = completion.choices[0]['message'].content

    return content


classify_comment_sentiment_prompt = """Given the following reddit comment, please say if the sentiment is NEGATIVE, NEUTRAL, or POSITIVE. 

The sentiment must be one of those three choices. Please only return one of those three choices.

Comment: {comment}
"""

tag_comment_prompt = """Given the following reddit comment for a product, add the following tags if the tag applies to the comment. Each tag has a tag name and a criteria for when it applies. 
The final answer for Tags can contain zero or more comma separated tags. 
Please only return the tags that apply. If no tags apply, return nothing (ie empty string).

Tag Name: PRICING
Tag Criteria: Comment mentions pricing of the product
Tag Name: COMPETITOR
Tag Criteria: Comment mentions a competitor of the product
Tag Name: COMPLAINT
Tag Criteria: Comment is a complaint of the product
Tag Name: PRAISE
Tag Criteria: Comment praises the product in any way
Tag Name: FEATURE_REQUEST
Tag Criteria: Comment is requesting a feature the author wishes the product has.

Comment: {comment}
Tags:
"""

# PRAW Reddit instance creation
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,     # replace with your client id
    client_secret=REDDIT_CLIENT_SECRET,  # replace with your client secret
    password="",      # replace with your password
    user_agent=f"Comment Extraction (by u/{REDDIT_USERNAME})",    # replace with your user agent
    username=REDDIT_USERNAME    # replace with your username
)

def add_reddit_comments_to_list(reddit_url):
    comment_list = []

    # Submission URL or id
    submission = reddit.submission(url=reddit_url)

    # Replace MoreComments with their corresponding comments
    submission.comments.replace_more(limit=None)

    # Iterate over all comments and write to CSV
    for comment in submission.comments.list():
        # comment created date
        utc_timestamp = comment.created_utc
        dt_object = datetime.utcfromtimestamp(utc_timestamp)
        formatted_date = dt_object.strftime("%Y-%m-%d")

        sentiment = call_inference(
            "gpt-3.5-turbo", 
            classify_comment_sentiment_prompt.format(comment=comment.body),
            ["product_research_app"]
        )
        tags = call_inference(
            "gpt-3.5-turbo", 
            tag_comment_prompt.format(comment=comment.body),
            ["product_research_app"]
        )

        row = [reddit_url, comment.id, comment.parent_id, str(comment.author), comment.body, sentiment, tags, formatted_date]
        print(row)
        comment_list.append(row)

    return comment_list


def create_data(reddit_urls):    
    comments_list = [["reddit_url", "comment_id", "comment_parent_id", "comment_author", "comment_text", "sentiment", "tags", "post_date"]]

    for reddit_url in reddit_urls:
        comments_list += add_reddit_comments_to_list(reddit_url)


def get_reddit_urls_from_search(search_query):
    params = {
        "engine": "google",
        "num": 100,
        "q": f"site:reddit.com {search_query}",
        "api_key": SERP_API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results["organic_results"]
    reddit_links = [result['link'] for result in results["organic_results"]]

    return reddit_links

def write_data_to_csv(filename, data):
    # TODO: This should probably write one row at a time in case it breaks midway
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for row in data:
            writer.writerow(row)


if __name__ == "__main__":
    reddit_urls = get_reddit_urls_from_search("avalara vs shopify tax")
    data = create_data(reddit_urls)
    write_data_to_csv(filename, data)

