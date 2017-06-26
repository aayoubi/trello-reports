from collections import defaultdict, Counter
from itertools import groupby
from datetime import datetime, timedelta
import argparse
import logging

from delorean import Delorean
from trello import TrelloApi

# cache member id and full names
board_members = {}


class Action(object):
    def __init__(self, action_type, member_name, date, card_name):
        self.action_type = action_type
        self.member_name = member_name
        self.date = date
        self.card_name = card_name
        self.desc = None

    def __str__(self):
        return "{} - {} - {} - {} - {}".format(self.action_type,
                                               self.member_name, self.date,
                                               self.card_name, self.desc)


class ArchiveAction(Action):
    def __init__(self, action_data, *args):
        super(self.__class__, self).__init__(*args)
        self.desc = 'Archived' \
            if action_data['old']['closed'] == False else 'Unarchived'
        self.archived = True if action_data['old']['closed'] == False else False

    @classmethod
    def describe_actions(cls, actions):
        print "# archived/unarchived"
        print "- {} cards were archived this week".format(
            len([action for action in actions if action.archived]))
        print "- {} cards were unarchived this week".format(
            len([action for action in actions if not action.archived]))


class MoveCardAction(Action):
    def __init__(self, action_data, *args):
        super(self.__class__, self).__init__(*args)
        self.desc = 'Moved from {} to {}'.format(
            action_data['listBefore']['name'], action_data['listAfter']['name'])

    @classmethod
    def describe_actions(cls, actions):
        print "# moving cards"
        top_moved = Counter([action.card_name for action in actions])
        print "- Top 3 most moved cards around the board:"
        for card in top_moved.most_common(3):
            print "    - {} [{} times]".format(card[0], card[1])


class AddRemoveMember(Action):
    def __init__(self, action_data, *args):
        super(self.__class__, self).__init__(*args)
        self.member_name = board_members.get(action_data['idMember'])
        self.added = True if self.action_type == 'addMemberToCard' else False
        self.desc = '{} member {}'.format(
            'Added' if self.action_type == 'addMemberToCard' else 'Removed',
            action_data['idMember'])

    @classmethod
    def describe_actions(cls, actions):
        print "# added members"
        top_added = Counter([action.member_name
                            for action in actions if action.added])
        top_removed = Counter([action.member_name
                               for action in actions if not action.added])
        print "- added to a card:"
        for m in top_added.most_common(5):
            print "    - {} [{} times]".format(m[0], m[1])
        print "- removed from a card:"
        for m in top_removed.most_common(5):
            print "    - {} [{} times]".format(m[0], m[1])


def transform_action(action):
    common = (action['type'], action['memberCreator']['fullName'],
              action['date'], action['data']['card']['name'])
    if action['type'] == 'updateCard' and 'closed' in action['data']['old']:
        return ArchiveAction(action['data'], *common)
    elif action['type'] == 'updateCard' and 'listBefore' in action['data']:
        return MoveCardAction(action['data'], *common)
    elif action['type'] in ('addMemberToCard', 'removeMemberFromCard'):
        return AddRemoveMember(action['data'], *common)
    else:
        raise Exception('Unsupported action type found: {}'.format(action))


def get_cet_timestamp_from_mongoid(object_id):
    return datetime.utcfromtimestamp(int(object_id[0:8], 16))


def trello_add_card_creation_date(cards):
    for card in cards:
        creation_date = get_cet_timestamp_from_mongoid(card['id'])
        card['timeDelta'] = (datetime.utcnow() - creation_date)
    return cards


def group_by_list(cards):
    agg = defaultdict(list)
    map(lambda card: agg[card['idList']].append(card), cards)
    return dict(agg)


def replace_id_by_label(lists, trello):
    return dict((trello.lists.get(key)['name'], value)
                for key, value in lists.items())


def print_lists_to_csv(lists):
    for list_name, cards in lists.items():
        for card in cards:
            print list_name, card['name'], card['timeDelta'], card['idMembers']


def describe_last_week_actions(actions):
    groups = groupby(sorted(actions, key=lambda a: a.__class__),
                     lambda a: a.__class__)
    for key, group in groups:
        key.describe_actions(list(group))
        print "---"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--client-api-key",
                        help="your app's client api key",
                        action="store", required=True)
    parser.add_argument("-t", "--token", help="your app's access token",
                        action="store", required=True)
    parser.add_argument("-b", "--board-id", help="your trello board id",
                        action="store", required=True)
    args = vars(parser.parse_args())

    log_format = '%(asctime)s - %(name)s - %(levelname)s %(message)s'
    logging.basicConfig(format=log_format, level=logging.WARN)

    trello = TrelloApi(args['client_api_key'])
    trello.set_token(args['token'])

    fields = 'fields=id,idMembers,idLabels,idList,shortUrl,dateLastActivity,\
name'
    cards = trello.boards.get_card(args['board_id'], fields=fields)
    cards = trello_add_card_creation_date(cards)
    cards.sort(key=lambda c: c['timeDelta'])
    lists = group_by_list(cards)
    lists = replace_id_by_label(lists, trello)

    members = trello.boards.get('{}/members'.format(args['board_id']))
    for member in members:
        board_members[member['id']] = member['fullName']

    last_week = Delorean() - timedelta(weeks=1)
    print("Since {} - {}".format(last_week.humanize(), last_week.date))

    action_filter = 'filter=createCard,deleteCard,updateCard:closed,\
addMemberToCard,removeMemberFromCard,updateCard:idList'
    actions = trello.boards.get('{}/actions?limit=1000&filter={}&since={}'
                                .format(args['board_id'],
                                        action_filter,
                                        last_week.date))
    # TODO add paging support if we go over 1000
    if len(actions) == 1000:
        logging.warn('the number of retried actions is over 1000, you may \
be missing other actions that occurred during the last week, \
please support paging')

    simple_actions = map(lambda a: transform_action(a), actions)
    describe_last_week_actions(simple_actions)
    print "---"
    for action in simple_actions:
        print action


if __name__ == '__main__':
    main()
