from collections import defaultdict

from requests_oauthlib import OAuth1
from requests_oauthlib import OAuth1Session
from pprint import pprint
import requests



def trello_api_request(request, auth):
    url = 'https://api.trello.com/%s' % request
    r = requests.get(url, auth=auth)
    print r.status_code
    return r.json()


def get_trello_list_name(id, auth):
    return trello_api_request('/1/lists/%s?fields=name' % id, auth)['name']


def get_aggregate_by_list(cards):
    agg = defaultdict(list)
    map(lambda card: agg[card['idList']].append(card), cards)
    return agg


def get_oauth_token(client_api_key, client_api_secret, app_name, expiration='30days', scope='read'):
    '''
    Retrieves an access token from Trello using OAuth1

        client_api_key => the application key created at https://trello.com/app-key

        client_api_secret => the secret key provided also at https://trello.com/app-key

        app_name => the application name as it will appear in https://trello.com/me/account

        expiration => string, expiration period of the access token, defaults to '30days'

        scope => string, scope permissions of your token, default to 'read' (other possible value 'read,write')

    :return: access_token
    '''
    request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
    authorize_url = 'https://trello.com/1/OAuthAuthorizeToken'
    access_token_url = 'https://trello.com/1/OAuthGetAccessToken'

    oauth = OAuth1Session(client_api_key, client_secret=client_api_secret)
    fetch_response = oauth.fetch_request_token(request_token_url)
    resource_owner_key = fetch_response.get('oauth_token')
    resource_owner_secret = fetch_response.get('oauth_token_secret')
    authorization_url = oauth.authorization_url(authorize_url + '?name=%s&expiration=%s&scope=%s' % (app_name, expiration, scope))

    print('Please go here and authorize,', authorization_url)
    oauth_verifier = raw_input('Paste the full verification code here: ')
    session = OAuth1Session(client_api_key,
                            client_secret=client_api_secret,
                            resource_owner_key=resource_owner_key,
                            resource_owner_secret=resource_owner_secret,
                            verifier=oauth_verifier)
    access_token = session.fetch_access_token(access_token_url)
    print("Access token:")
    pprint(access_token)
    return access_token


def get_oauth(client_api, client_secret, token, token_secret):
    oauth = OAuth1(client_key=client_api,
                   client_secret=client_secret,
                   resource_owner_key=token,
                   resource_owner_secret=token_secret)
    return oauth


def main():
    from secrets.api import TRELLO_API_KEY, TRELLO_API_SECRET, TOKEN, TOKEN_SECRET, APP_NAME
    from secrets.trello import BOARD_ID

    # access_token = get_oauth_token(TRELLO_API_KEY, TRELLO_API_SECRET, APP_NAME)
    auth = get_oauth(TRELLO_API_KEY, TRELLO_API_SECRET, TOKEN, TOKEN_SECRET)

    fields = 'fields=name,id,idMembers,idLabels,idList,shortUrl'
    cards = trello_api_request('/1/boards/%s/cards?limit=1000&%s' % (BOARD_ID, fields), auth)
    agg = get_aggregate_by_list(cards)

    for k, v in agg.items():
        print k, v

if __name__ == '__main__':
    main()
