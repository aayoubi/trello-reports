from collections import defaultdict

from requests_oauthlib import OAuth1
from requests_oauthlib import OAuth1Session
from pprint import pprint
import requests
import logging
import operator


class Trello():
    def __init__(self, auth):
        self.auth = auth

    def get(self, request):
        url = 'https://api.trello.com/%s' % request
        r = requests.get(url, auth=self.auth)
        return r.json()

    def get_name_of_list(self, list_name):
        return self.get('/1/lists/%s?fields=name' % list_name)['name']

    def get_name_of_label(self, label_name):
        return self.get('/1/label/%s?fields=name' % label_name)['name']

    def get_name_of_member(self, member_name):
        return self.get('/1/member/%s?fields=name' % member_name)['name']


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


def get_auth(client_api, client_secret, token, token_secret):
    oauth = OAuth1(client_key=client_api,
                   client_secret=client_secret,
                   resource_owner_key=token,
                   resource_owner_secret=token_secret)
    return oauth


def trello_add_card_creation_date(cards):
    from trello_model import get_cet_timestamp_from_mongoid, get_datetime_from_utctimestamp, get_card_elapsed_time
    map(lambda card: operator.setitem(card,
                                      'timeDelta',
                                      get_card_elapsed_time(get_cet_timestamp_from_mongoid(card['id']),
                                                            get_datetime_from_utctimestamp(card['dateLastActivity']))),
        cards)
    return cards


def aggregate_cards_by_list(cards, trello):
    agg = defaultdict(list)
    agg_with_labels = defaultdict(list)
    map(lambda card: agg[card['idList']].append(card), cards)
    for key in agg:
        agg_with_labels[trello.get_name_of_list(key)] = agg[key] # INFO retrieve label of lists after aggregation
    return agg_with_labels


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s %(message)s', level=logging.DEBUG)

    # FIXME use argparse to switch between oauth token generation or other commands
    from secrets.api import TRELLO_API_KEY, TRELLO_API_SECRET, TOKEN, TOKEN_SECRET, APP_NAME
    from secrets.trello import BOARD_ID

    # access_token = get_oauth_token(TRELLO_API_KEY, TRELLO_API_SECRET, APP_NAME)
    trello = Trello(get_auth(TRELLO_API_KEY, TRELLO_API_SECRET, TOKEN, TOKEN_SECRET))

    fields = 'fields=name,id,idMembers,idLabels,idList,shortUrl,dateLastActivity'
    cards = trello.get('/1/boards/%s/cards?limit=1000&%s' % (BOARD_ID, fields))

    if len(cards) == 1000:
        logging.warn("WARNING - retrieve 1000 cards, you may be missing other cards, considering Paging")
        logging.warn("Check this: https://developers.trello.com/get-started/intro#paging")

    logging.info("Processing [%d] cards" % len(cards))

    cards = trello_add_card_creation_date(cards)
    agg = aggregate_cards_by_list(cards, trello)

    logging.info(dict(agg))
    pprint(sorted(agg['In-progress'], key=lambda c: c['timeDelta']))


if __name__ == '__main__':
    main()
