
from threading import Timer
import tweepy

try:
    from atri_bot.twitter import config
    client = tweepy.Client(bearer_token=config.bearer_token)
    client.session.proxies = {"https": config.proxy}
except:
    print('please create config.py in twitter folder whitch contains bearer_token and proxy')
    pass


timer = None


def get_users_tweets(users=None, usernames=None, uids=None, max_results=10, end_time=None):
    """
    获取用户最近的推特

    Parameters
        ----------
        users : List[User]
            用户列表 通过 get_users 方法获取 通过此参数获取推特，内部可以减少一次请求
        usernames : List[str]
            用户名列表, 用户名是推特的唯一名称, 不是用户昵称
        uids : List[str]
            用户名uid 列表
        end_time : Union[datetime.datetime, str]
            YYYY-MM-DDTHH:mm:ssZ (ISO 8601/RFC 3339). The newest or most recent
            UTC timestamp from which the Tweets will be provided. Only the 3200
            most recent Tweets are available. Timestamp is in second
            granularity and is inclusive (for example, 12:00:01 includes the
            first second of the minute). Minimum allowable time is
            2010-11-06T00:00:01Z

            Please note that this parameter does not support a millisecond
            value.
        max_results : int
            Specifies the number of Tweets to try and retrieve, up to a maximum
            of 100 per distinct request. By default, 10 results are returned if
            this parameter is not supplied. The minimum permitted value is 5.
            It is possible to receive less than the ``max_results`` per request
            throughout the pagination process.
    """
    results = []
    if users is None:
        users = get_users(usernames=usernames, uids=uids)

    for user in users:
        uid = user.get('id')
        tweets = client.get_users_tweets(
            id=uid, max_results=max_results, end_time=end_time, 
            tweet_fields=['created_at', 'entities'],
            media_fields=['media_key', 'duration_ms', 'preview_image_url', 'url', 'type', 'height', 'width'],
            exclude=['retweets', 'replies'],
            expansions=['attachments.media_keys']
        )

        media = tweets.includes.get('media') if tweets.includes is not None else None

        if tweets.data is not None:
            for tweet in tweets.data:

                media_keys = tweet.attachments.get('media_keys') if tweet.attachments is not None else None

                media_filter = []
                if media_keys is not None and media is not None:
                    for media_key in media_keys:
                        for m in media:
                            if m.media_key == media_key:
                                media_filter.append(m.data)
                                break

                results.append({
                    'text': tweet.text,
                    'tid': tweet.id,
                    'uid': uid,
                    'user': user,
                    'media': media_filter,
                    'created_at': tweet.created_at,
                    'hashtags': tweet.entities.get('hashtags') if tweet.entities is not None else None,
                })
    return results


def get_users(usernames=None, uids=None):
    users = client.get_users(usernames=usernames, ids=uids, user_fields=['profile_image_url', 'description'])
    user_list = []
    if users.data is not None:
        for user in users.data:
            if user.data is not None:
                user_list.append(user.data)
    return user_list


def get_user_ids(users=None, usernames=None):
    return [user.get('id') for user in (users if users is not None else get_users(usernames=usernames))]


def start_observe_tweets(users=None, usernames=None, uids=None, callback=None, interval=10, max_results=10, end_time=None):
    stop_observe_tweets()

    global timer
    timer = Timer(interval=interval, function=_do_observe_tweets, args=(users, usernames, uids, callback, interval, max_results, end_time))
    timer.start()


def stop_observe_tweets():
    global timer
    if timer is not None:
        timer.cancel()
        timer = None


def _do_observe_tweets(users=None, usernames=None, uids=None, callback=None, interval=10, max_results=10, end_time=None):
    if callback is not None:
        callback(get_users_tweets(users=users, usernames=usernames, uids=uids, max_results=max_results, end_time=end_time))
    
    global timer
    if timer is None:
        return
    start_observe_tweets(users=users, usernames=usernames, uids=uids, callback=callback, interval=interval, max_results=max_results, end_time=end_time)


def test():
    usernames = ['Genshin_7', 'moke14']
    users = get_users(usernames)
    print('uids', get_user_ids(users=users))

    print('test')
    start_observe_tweets(users=users, callback=lambda tweets: print(tweets))
    print('pop stack: test')


if __name__ == "__main__":
    test()