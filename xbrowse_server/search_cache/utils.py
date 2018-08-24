import hashlib

from django.conf import settings
import pymongo
import logging


def save_results_for_spec(project_id, search_spec, results):
    """
    Cache the search results for project_id defined by search_spec

    Returns: search ID - just a hash of the search spec
    """
    search_hash = get_hash_of_search_spec(search_spec)
    try:
        settings.UTILS_DB.search_cache.update({'project_id': project_id, 'search_hash': search_hash},
            {'$set': {'results': results, 'search_spec': search_spec}},
            upsert=True
        )
    except pymongo.errors.InvalidDocument:
        settings.UTILS_DB.search_cache.update({'project_id': project_id, 'search_hash': search_hash},
            {'$set': {'search_spec': search_spec}, '$unset': {'results': 1}},
            upsert=True
        )
    return search_hash


def get_hash_of_search_spec(search_spec):
    hasher = hashlib.md5()
    hasher.update(str(search_spec))
    hashed = hasher.hexdigest()[:8]
    return hashed


def get_cached_results(project_id, search_hash):
    """
    Returns:
        tuple of (search spec, results)
        results could be None if has been discarded
        returns None, None if can't find document, but that shouldn't happen..
    """
    doc = settings.UTILS_DB.search_cache.find_one({'project_id': project_id, 'search_hash': search_hash})
    if not doc:
        return None, None
    return doc['search_spec'], doc.get('results')


def clear_project_results_cache(project_id):
    """
    Remove all search results for the given project
    """
    settings.UTILS_DB.search_cache.update({'project_id': project_id}, {'$unset': {'results': 1}}, multi=True)


def clear_results_cache():
    """
    Remove all search results
    """
    settings.UTILS_DB.search_cache.update({}, {'$unset': {'results': 1}}, multi=True)
