
import tweepy

try:
    import config
    client = tweepy.Client(bearer_token=config.bearer_token)
    client.session.proxies={"https": config.proxy}
except:
    print('please create config.py in twitter folder whitch contains bearer_token and proxy')
    pass


def users_tweets(usernames, max_results=10, end_time=None):
    """
    获取用户最近的推特

    Parameters
        ----------
        usernames : List[str]
            用户名列表, 用户名是推特的唯一名称, 不是用户昵称
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
    tweets = []
    for user in users(usernames):
        uid = user.get('id')
        username = user.get('username')
        _tweets = client.get_users_tweets(id=uid, max_results=max_results, end_time=end_time)
        for tweet in _tweets.data:
            tweets.append({
                'text': tweet.text,
                'tid': tweet.id,
                'uid': uid,
                'username': username
            })
    return tweets


def users(usernames):
    users = client.get_users(usernames=usernames)
    user_list = []
    for user in users.data:
        user_list.append({
            'id': user.id,
            'username': user.username
        })
    return user_list


def test():
    for tweet in users_tweets(['Friends___A'], max_results=15):
        print(tweet)

