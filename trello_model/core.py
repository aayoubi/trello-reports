
from datetime import datetime

def get_cet_timestamp_from_mongoid(object_id):
    return datetime.utcfromtimestamp(int(object_id[0:8], 16))


def get_datetime_from_utctimestamp(utctimestamp):
    return datetime.strptime(utctimestamp, "%Y-%m-%dT%H:%M:%S.%fZ")


def get_card_elapsed_time(creationDate, dateLastActivity):
    return dateLastActivity - creationDate